import json
import sys
import tkinter as tk
from enum import Enum
from tkinter import ttk

from PIL import Image, ImageTk
from ttkthemes import ThemedStyle

import src.resource as resource
from src.circuit import Circuit

THEME_NAME = "black"


class Editor:
    DIMENSIONS = "1300x1300"
    BG_COLOR = "#181818"
    CANVAS_COLOR = "#404040"
    HIGH_COLOR = "#00FF21"
    LOW_COLOR = "#000000"

    circuit = Circuit()

    object_data = json.load(open(resource.path("src/objects.json")))
    gate_data = object_data["gates"]
    input_data = object_data["inputs"]
    output_data = object_data["outputs"]

    objects = []
    nodes = []
    edges = []
    loaded_assets = {}

    state = None
    grabbed_object = None
    temp_edge = None

    class GrabState(Enum):
        CANVAS = 1
        OBJECT = 2
        NODE = 3

    def __init__(self, root, window):
        self.window = window
        self.root = root

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        self.window.geometry(self.DIMENSIONS)
        self.window.title("Logic Gates")
        self.window.configure(background=self.BG_COLOR)

        style = ThemedStyle(self.window)
        style.set_theme(THEME_NAME)

        self.sidebar = ttk.LabelFrame(self.window, text="Objects", padding=9)
        self.gate_frame = ttk.LabelFrame(self.sidebar, text="Gates", padding=4)
        self.gate_buttons = []
        self.input_frame = ttk.LabelFrame(
            self.sidebar, text="Inputs", padding=4
        )
        self.input_buttons = []
        self.output_frame = ttk.LabelFrame(
            self.sidebar, text="Outputs", padding=4
        )
        self.output_buttons = []

        self.frame = ttk.LabelFrame(self.window, text="Diagram", padding=2)
        self.diagram = tk.Canvas(self.frame, bg=self.CANVAS_COLOR)

        gate_dimensions = self.gate_data["dimensions"]
        for title in self.object_data["gates"]["gate_types"]:
            filename = "img/" + title + ".png"
            asset = ImageTk.PhotoImage(
                Image.open(resource.path(filename)).resize(gate_dimensions)
            )
            self.loaded_assets[title] = asset

            button = ttk.Button(self.gate_frame, text=title, width=10)
            button.bind("<ButtonPress-1>", self.draw_gate)
            self.gate_buttons.append(button)

        for input in self.input_data:
            default_filename = self.input_data[input]["default_asset"]
            dimensions = self.input_data[input]["dimensions"]
            asset = ImageTk.PhotoImage(
                Image.open(resource.path(default_filename)).resize(dimensions)
            )
            self.loaded_assets[input] = asset

            if self.input_data[input].get("changed_asset"):
                changed_filename = self.input_data[input]["changed_asset"]
                asset = ImageTk.PhotoImage(
                    Image.open(resource.path(changed_filename)).resize(
                        dimensions
                    )
                )
                self.loaded_assets[(input + "_changed")] = asset

            button = ttk.Button(self.input_frame, text=input, width=10)
            button.bind("<ButtonPress-1>", self.draw_input)
            self.input_buttons.append(button)

        for output in self.output_data:
            default_filename = self.output_data[output]["default_asset"]
            dimensions = self.output_data[output]["dimensions"]
            asset = ImageTk.PhotoImage(
                Image.open(resource.path(default_filename)).resize(dimensions)
            )
            self.loaded_assets[output] = asset

            changed_filename = self.output_data[output]["changed_asset"]
            asset = ImageTk.PhotoImage(
                Image.open(resource.path(changed_filename)).resize(dimensions)
            )
            self.loaded_assets[(output + "_changed")] = asset

            button = ttk.Button(self.output_frame, text=output, width=10)
            button.bind("<ButtonPress-1>", self.draw_output)
            self.output_buttons.append(button)

        self.diagram.bind("<MouseWheel>", self.do_zoom)
        self.diagram.bind("<ButtonPress-1>", self.down_handler)
        self.diagram.bind("<ButtonRelease-1>", self.up_handler)
        self.diagram.bind("<B1-Motion>", self.move_handler)

        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(1, weight=1)

        self.sidebar.rowconfigure(0, weight=0)
        self.sidebar.rowconfigure(1, weight=0)
        self.sidebar.rowconfigure(2, weight=1)
        self.sidebar.columnconfigure(0, weight=1)

        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        for i in range(len(self.gate_buttons)):
            self.gate_buttons[i].grid(row=i, column=0, sticky="EW")
        for i in range(len(self.input_buttons)):
            self.input_buttons[i].grid(row=i, column=0, sticky="EW")
        for i in range(len(self.output_buttons)):
            self.output_buttons[i].grid(row=i, column=0, sticky="EW")

        self.diagram.grid(row=0, column=0, sticky="NSEW")
        self.sidebar.grid(row=0, column=0, sticky="NS")
        self.gate_frame.grid(row=0, column=0, sticky="NSEW")
        self.input_frame.grid(row=1, column=0, sticky="NSEW")
        self.output_frame.grid(row=2, column=0, sticky="NSEW")
        self.frame.grid(row=0, column=1, sticky="NSEW")

    def adjust_coords(self, x, y, offset_coords):
        x0, y0, x1, y1 = offset_coords
        x0, x1 = x0 + x, x1 + x
        y0, y1 = y0 + y, y1 + y

        return [x0, y0, x1, y1]

    def draw_node(self, coords, color, type, object_id):
        x0, y0, x1, y1 = coords
        node = self.diagram.create_oval(x0, y0, x1, y1, fill=color)

        self.diagram.addtag_withtag(type, node)
        self.diagram.addtag_withtag("object" + str(object_id), node)
        self.diagram.tag_raise(node)
        self.nodes.append(node)

    def draw_gate(self, event):
        title = event.widget["text"]
        num_inputs = self.gate_data["gate_types"][title]
        node_fill_color = self.gate_data["node_fill"]

        center_x, center_y = (
            self.diagram.winfo_width() / 2,
            self.diagram.winfo_height() / 2,
        )
        gate = self.diagram.create_image(
            center_x, center_y, image=self.loaded_assets[title]
        )
        self.diagram.tag_raise(gate)
        self.objects.append(gate)

        self.circuit.add_node(gate, title, num_inputs)

        if num_inputs == 1:
            coords = self.gate_data["input_node_position"]
            adjusted_coords = self.adjust_coords(center_x, center_y, coords)
            self.draw_node(adjusted_coords, node_fill_color, "input0", gate)
        else:
            for i in range(num_inputs):
                coords = self.gate_data["two_input_node_positions"][i]
                adjusted_coords = self.adjust_coords(
                    center_x, center_y, coords
                )
                self.draw_node(
                    adjusted_coords, node_fill_color, "input" + str(i), gate
                )

        coords = self.gate_data["output_position"]
        adjusted_coords = self.adjust_coords(center_x, center_y, coords)
        self.draw_node(adjusted_coords, node_fill_color, "output", gate)

    def draw_input(self, event):
        title = event.widget["text"]
        node_fill_color = self.object_data["gates"]["node_fill"]

        center_x, center_y = (
            self.diagram.winfo_width() / 2,
            self.diagram.winfo_height() / 2,
        )
        input = self.diagram.create_image(
            center_x, center_y, image=self.loaded_assets[title]
        )
        self.diagram.tag_raise(input)
        self.objects.append(input)

        self.circuit.add_node(
            input, 0, 0, output=True if (title == "constant on") else False
        )

        output_coords = self.input_data[title]["output_position"]
        adjusted_output_coords = self.adjust_coords(
            center_x, center_y, output_coords
        )
        self.draw_node(
            adjusted_output_coords, node_fill_color, "output", input
        )

        if title == "switch":
            self.diagram.tag_bind(
                input,
                "<ButtonRelease-1>",
                lambda event: self.switch_click(event, input),
            )

    def draw_output(self, event):
        title = event.widget["text"]
        node_fill_color = self.object_data["gates"]["node_fill"]

        center_x, center_y = (
            self.diagram.winfo_width() / 2,
            self.diagram.winfo_height() / 2,
        )
        output = self.diagram.create_image(
            center_x, center_y, image=self.loaded_assets[title]
        )
        self.diagram.addtag_withtag("output_obj", output)
        self.diagram.tag_raise(output)
        self.objects.append(output)

        self.circuit.add_node(output, 0, 1)

        input_coords = self.output_data[title]["input_position"]
        adjusted_input_coords = self.adjust_coords(
            center_x, center_y, input_coords
        )
        self.draw_node(
            adjusted_input_coords, node_fill_color, "input0", output
        )

    def update_edges(self):
        high_nodes = []
        node_data = self.circuit.graph.nodes(data=True)

        for node in node_data:
            id = node[0]
            data = node[1]
            if data["output"] == True:
                high_nodes.append(id)

        for edge in self.edges:
            tags = self.diagram.gettags(edge)
            for tag in tags:
                if "start_gate" in tag:
                    id = int(tag.replace("start_gate", ""))
                    if id in high_nodes:
                        self.diagram.itemconfig(edge, fill=self.HIGH_COLOR)
                    else:
                        self.diagram.itemconfig(edge, fill=self.LOW_COLOR)
                elif "end_gate" in tag:
                    id = int(tag.replace("end_gate", ""))
                    tags = self.diagram.gettags(id)
                    if "output_obj" in tags:
                        input = self.circuit.graph.nodes[id]["input"][0]
                        self.lightbulb_changed(id, input)

    def switch_click(self, event, id):
        tags = self.diagram.gettags(id)
        if "on" in tags:
            default_asset = self.loaded_assets["switch"]
            self.diagram.itemconfig(id, image=default_asset)
            self.diagram.dtag(id, "on")
            self.circuit.change_output(id, False)
        else:
            on_asset = self.loaded_assets["switch_changed"]
            self.diagram.itemconfig(id, image=on_asset)
            self.diagram.addtag_withtag("on", id)
            self.circuit.change_output(id, True)
        self.update_edges()

    def lightbulb_changed(self, id, input):
        if input == False:
            default_asset = self.loaded_assets["lightbulb"]
            self.diagram.itemconfig(id, image=default_asset)
        else:
            changed_asset = self.loaded_assets["lightbulb_changed"]
            self.diagram.itemconfig(id, image=changed_asset)

    def contains_xy(self, coords, x, y):
        x1, y1, x2, y2 = coords
        if (x1 < x < x2) and (y1 < y < y2):
            return True
        else:
            return False

    def find_center_coords(self, coords):
        x1, y1, x2, y2 = coords
        x = (x1 + x2) / 2
        y = (y1 + y2) / 2
        return (x, y)

    def check_grab_state(self, x, y):
        for node in reversed(self.nodes):
            tags = self.diagram.gettags(node)
            coords = self.diagram.coords(node)
            touched = self.contains_xy(coords, x, y)
            output = "output" in tags

            if touched and output:
                self.grabbed_object = node
                return self.GrabState.NODE

        for object in reversed(self.objects):
            tags = self.diagram.gettags(object)
            touched = False
            for tag in tags:
                if tag == "current":
                    self.grabbed_object = object
                    return self.GrabState.OBJECT

        return self.GrabState.CANVAS

    def down_handler(self, event):
        x = int(self.diagram.canvasx(event.x))
        y = int(self.diagram.canvasy(event.y))
        self.state = self.check_grab_state(x, y)

        if self.state == self.GrabState.OBJECT:
            self.drag_x = x
            self.drag_y = y

        elif self.state == self.GrabState.CANVAS:
            self.diagram.scan_mark(event.x, event.y)

        elif self.state == self.GrabState.NODE:
            c_x, c_y = self.find_center_coords(
                self.diagram.coords(self.grabbed_object)
            )
            self.temp_edge = self.diagram.create_line(
                c_x, c_y, c_x, c_y, width=5
            )

    def up_handler(self, event):
        x = int(self.diagram.canvasx(event.x))
        y = int(self.diagram.canvasy(event.y))

        if self.state == self.GrabState.NODE:
            valid_edge = False
            edge = self.temp_edge
            start_node = self.grabbed_object
            start_node_tags = self.diagram.gettags(start_node)
            for tag in start_node_tags:
                if "object" in tag:
                    start_object_id = int(tag.replace("object", ""))

            for node in reversed(self.nodes):
                if valid_edge == False:
                    new_node = False
                    new_obj = False
                    is_input = False
                    has_input = False
                    coords = self.diagram.coords(node)

                    if self.contains_xy(coords, x, y):
                        if node != start_node:
                            new_node = True

                        tags = self.diagram.gettags(node)
                        for tag in tags:
                            if tag[0:5] == "input":
                                input_position = int(tag.replace("input", ""))
                                is_input = True
                            elif ("object" in tag) and (
                                int(tag.replace("object", ""))
                                != start_object_id
                            ):
                                end_obj_id = int(tag.replace("object", ""))
                                new_obj = True
                            elif tag == "has_input":
                                has_input = True

                        if (
                            new_node
                            and new_obj
                            and is_input
                            and not (has_input)
                        ):
                            valid_edge = True
                            self.edges.append(edge)

                            self.circuit.add_edge(
                                start_object_id, end_obj_id, input_position
                            )

                            x0, y0 = self.find_center_coords(
                                self.diagram.coords(self.grabbed_object)
                            )
                            x1, y1 = self.find_center_coords(
                                self.diagram.coords(node)
                            )
                            self.diagram.coords(edge, x0, y0, x1, y1)

                            start_tag = "start" + str(self.grabbed_object)
                            end_tag = "end" + str(node)
                            self.diagram.addtag_withtag(start_tag, edge)
                            self.diagram.addtag_withtag(end_tag, edge)
                            self.diagram.addtag_withtag(
                                "start_gate" + str(start_object_id), edge
                            )
                            self.diagram.addtag_withtag(
                                "end_gate" + str(end_obj_id), edge
                            )
                            self.diagram.addtag_withtag("has_input", node)

                            self.update_edges()

            if valid_edge == False:
                self.diagram.delete(self.temp_edge)

        self.object_grabbed = None
        self.temp_edge = None
        self.state = None

    def move_handler(self, event):
        x = int(self.diagram.canvasx(event.x))
        y = int(self.diagram.canvasy(event.y))

        if self.state == self.GrabState.OBJECT:
            diff_x = x - self.drag_x
            diff_y = y - self.drag_y

            self.drag_x = x
            self.drag_y = y
            self.diagram.move(self.grabbed_object, diff_x, diff_y)

            for node in self.diagram.find_withtag(
                "object" + str(self.grabbed_object)
            ):
                self.diagram.move(node, diff_x, diff_y)
                for edge in self.diagram.find_withtag("start" + str(node)):
                    x0, y0, x1, y1 = self.diagram.coords(edge)
                    self.diagram.coords(edge, x0 + diff_x, y0 + diff_y, x1, y1)
                for edge in self.diagram.find_withtag("end" + str(node)):
                    x0, y0, x1, y1 = self.diagram.coords(edge)
                    self.diagram.coords(edge, x0, y0, x1 + diff_x, y1 + diff_y)

        elif self.state == self.GrabState.CANVAS:
            self.diagram.scan_dragto(event.x, event.y, gain=1)

        elif self.state == self.GrabState.NODE:
            x0, y0 = self.find_center_coords(
                self.diagram.coords(self.grabbed_object)
            )
            self.diagram.coords(self.temp_edge, x0, y0, x, y)

    def do_zoom(self, event):
        x = self.diagram.canvasx(event.x)
        y = self.diagram.canvasy(event.y)
        factor = 1.001**event.delta
        self.diagram.scale(tk.ALL, x, y, factor, factor)

    def on_close(self):
        self.window.destroy()
        sys.exit()


def main():
    root = tk.Tk()
    root.withdraw()
    window = tk.Toplevel(root)
    app = Editor(root, window)
    root.mainloop()


if __name__ == "__main__":
    main()
