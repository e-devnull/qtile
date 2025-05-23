# Copyright (c) 2020 Guangwang Huang
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import json
import os
import re
import subprocess

import pytest

import libqtile.bar
import libqtile.config
import libqtile.layout
import libqtile.widget
from libqtile.command.base import expose_command
from libqtile.confreader import Config
from libqtile.lazy import lazy


class ServerConfig(Config):
    class KwargWidget(libqtile.widget.base._TextBox):
        @expose_command
        def test_kwargs(self, *, a: int = 0):
            return {"value": a}

    auto_fullscreen = True
    keys = [
        libqtile.config.Key(["mod4"], "Return", lazy.spawn("xterm")),
        libqtile.config.Key(["mod4"], "t", lazy.spawn("xterm"), desc="dummy description"),
        libqtile.config.Key([], "y", desc="noop"),
        libqtile.config.KeyChord(
            ["mod4"],
            "q",
            [
                libqtile.config.KeyChord(
                    [],
                    "q",
                    [
                        libqtile.config.Key([], "a", lazy.togroup("a")),
                    ],
                ),  # unnamed
                libqtile.config.Key([], "b", lazy.togroup("b")),
            ],
            mode="named",
        ),
    ]
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
    ]
    layouts = [
        libqtile.layout.Stack(num_stacks=1),
        libqtile.layout.Stack(num_stacks=2),
        libqtile.layout.Stack(num_stacks=3),
    ]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [libqtile.widget.TextBox(name="one"), KwargWidget("")],
                20,
            ),
        ),
        libqtile.config.Screen(
            bottom=libqtile.bar.Bar(
                [
                    libqtile.widget.TextBox(name="two"),
                ],
                20,
            ),
        ),
    ]


server_config = pytest.mark.parametrize("manager", [ServerConfig], indirect=True)


def run_qtile_cmd(args, no_json_loads=False):
    cmd = os.path.join(os.path.dirname(__file__), "..", "bin", "qtile")
    argv = [cmd, "cmd-obj"]
    argv.extend(args.split())
    pipe = subprocess.Popen(argv, stdout=subprocess.PIPE)
    output, _ = pipe.communicate()
    output = output.decode()
    if not output:
        return False
    if no_json_loads:
        return output
    return json.loads(output)


@server_config
def test_qtile_cmd(manager):
    manager.test_window("foo")
    wid = manager.c.window.info()["id"]

    for obj in ["window", "group", "screen"]:
        assert run_qtile_cmd(f"-s {manager.sockfile} -o {obj} -f info")

    layout = run_qtile_cmd(f"-s {manager.sockfile} -o layout -f info")
    assert layout["name"] == "stack"
    assert layout["group"] == "a"

    window = run_qtile_cmd(f"-s {manager.sockfile} -o window {wid} -f info")
    assert window["id"] == wid
    assert window["name"] == "foo"
    assert window["group"] == "a"

    group = run_qtile_cmd("-s {} -o group {} -f info".format(manager.sockfile, "a"))
    assert group["name"] == "a"
    assert group["screen"] == 0
    assert group["layouts"] == ["stack", "stack", "stack"]
    assert group["focus"] == "foo"

    assert run_qtile_cmd(f"-s {manager.sockfile} -o screen {0} -f info") == {
        "height": 600,
        "index": 0,
        "width": 800,
        "x": 0,
        "y": 0,
    }

    bar = run_qtile_cmd("-s {} -o bar {} -f info".format(manager.sockfile, "bottom"))
    assert bar["height"] == 20
    assert bar["width"] == 800
    assert bar["size"] == 20
    assert bar["position"] == "bottom"


@server_config
def test_display_kb(manager):
    from pprint import pprint

    cmd = f"-s {manager.sockfile} -o root -f display_kb"
    table = run_qtile_cmd(cmd)
    print(table)
    pprint(table)
    assert table.count("\n") >= 2
    assert re.match(r"(?m)^Mode\s{3,}KeySym\s{3,}Mod\s{3,}Command\s{3,}Desc\s*$", table)
    assert re.search(r"(?m)^<root>\s{3,}Return\s{3,}mod4\s{3,}spawn\('xterm'\)\s*$", table)
    assert re.search(
        r"(?m)^<root>\s{3,}t\s{3,}mod4\s{3,}spawn\('xterm'\)\s{3,}dummy description\s*$", table
    )
    assert re.search(r"(?m)^<root>\s{3,}q\s{3,}mod4\s{13,}Enter named mode\s*$", table)
    assert re.search(r"(?m)^named\s{3,}q\s{13,}Enter <unnamed> mode\s*$", table)
    assert re.search(r"(?m)^named\s{3,}b\s{9,}togroup\('b'\)\s*$", table)
    assert re.search(r"(?m)^named>_\s{3,}a\s{9,}togroup\('a'\)\s*$", table)
    assert re.search(r"(?m)^<root>\s{3,}y\s{9,}\s*$", table) is None


@server_config
def test_cmd_obj_root_node(manager):
    base = f"-s {manager.sockfile} -f ok"
    cmd_no_root = base
    cmd_with_root = f"{base} -o root"

    assert run_qtile_cmd(cmd_no_root, no_json_loads=True) == run_qtile_cmd(
        cmd_with_root, no_json_loads=True
    )


@server_config
def test_cmd_obj_kwarg(manager):
    cmd = f"-s {manager.sockfile} -o widget kwargwidget -f test_kwargs -k a=2"
    result = run_qtile_cmd(cmd)

    # This confirms that value has correctly been converted to int
    assert result["value"] == 2
