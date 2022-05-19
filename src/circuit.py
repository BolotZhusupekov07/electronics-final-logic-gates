import networkx as nx


class Circuit:
    def __init__(self):
        self.graph = nx.DiGraph()

        self.logic = {
            "or": (lambda in1, in2: in1 or in2),
            "and": (lambda in1, in2: in1 and in2),
            "not": (lambda in1: not (in1)),
            "nor": (lambda in1, in2: not (in1 or in2)),
            "nand": (lambda in1, in2: not (in1 and in2)),
            "xor": (lambda in1, in2: in1 != in2),
            "xnor": (lambda in1, in2: in1 == in2),
            "buffer": (lambda in1: in1),
        }

    def change_output(self, id, val):
        self.graph.nodes[id]["output"] = val
        self.update(id)

    def update(self, start_id):
        for edge in self.graph.out_edges(start_id):
            curr_output = self.graph.nodes[start_id]["output"]
            input_position = self.graph.edges[edge[0], edge[1]]["position"]
            out_node_id = edge[1]

            self.logicize_node(out_node_id, input_position, curr_output)
            self.update(out_node_id)

    def logicize_node(self, id, input_position, input_value):
        node = self.graph.nodes[id]
        node["input"][input_position] = input_value

        if node["logic"]:
            logic_type = node["logic"]
            inputs = node["input"]

            if len(inputs) == 2:
                output = self.logic[logic_type](inputs[0], inputs[1])
            else:
                output = self.logic[logic_type](inputs[0])
            self.graph.nodes[id]["output"] = output

    def add_node(self, id, logic, num_inputs, output=False):
        self.graph.add_node(
            id, logic=logic, input=[False] * num_inputs, output=output
        )
        self.update(id)

    def add_edge(self, start_id, end_id, position):
        self.graph.add_edge(start_id, end_id, position=position)
        self.update(start_id)
