import itertools

import sympy
import numpy as np
import networkx as nx
import tqdm

from matplotlib import pyplot as plt

import cirq
import tensorflow as tf
import tensorflow_quantum as tfq


class QAOAProblem:

    def __init__(self, graph: nx.Graph, p=8):
        self.p = p
        self.graph = graph
        self.qubits = [cirq.GridQubit(0, i) for i in range(self.graph.number_of_nodes())]
        self.params = sympy.symbols("q0:%d" % (2 * p))

        self.circuit = self.__make_circuit()
        self.initial_state = self.__make_initial_state()

        self.cost_fn = self.__make_output_cost()
        self.optimizer = tf.keras.optimizers.Adam(lr=0.01)
        self.model = tf.keras.models.Sequential([
            tf.keras.layers.Input(shape=(), dtype=tf.dtypes.string),
            tfq.layers.PQC(self.circuit, self.cost_fn,
                           differentiator=tfq.differentiators.Adjoint())
        ])

    def __make_circuit(self):
        qaoa_circuit = cirq.Circuit()
        for i in range(self.p):
            # Cost Hamiltonian
            for edge in self.graph.edges():
                qaoa_circuit += cirq.CNOT(self.qubits[edge[0]], self.qubits[edge[1]])
                qaoa_circuit += cirq.rz(self.params[2 * i]).on(self.qubits[edge[1]])
                qaoa_circuit += cirq.CNOT(self.qubits[edge[0]], self.qubits[edge[1]])
            # Mixing Hamiltonian
            for j in range(len(self.qubits)):
                qaoa_circuit += cirq.rx(2 * self.params[2 * i + 1]).on(self.qubits[j])
        return qaoa_circuit

    def __make_initial_state(self):
        initial = cirq.Circuit()
        for i in self.qubits:
            initial.append(cirq.H(i))
        inputs = tfq.convert_to_tensor([initial])
        return inputs

    def __make_output_cost(self):
        cost = 0
        for edge in self.graph.edges():
            cost += cirq.PauliString(
                1 / 2 * cirq.Z(self.qubits[edge[0]]) * cirq.Z(self.qubits[edge[1]]))
        return cost

    def solve_complete(self):
        subsets_list = itertools.chain.from_iterable(
            itertools.combinations(self.graph.nodes(), r) for r in range(self.graph.number_of_nodes() + 1))
        max_cut = [nx.algorithms.cuts.cut_size(self.graph, assignment) for assignment in subsets_list]
        return np.max(max_cut)

    def sample_solutions(self, parameters=None):
        if parameters is None:
            parameters = self.model.trainable_variables
        sample_circuit = tfq.layers.AddCircuit()(self.initial_state, append=self.circuit)
        output = tfq.layers.Sample()(sample_circuit, symbol_names=self.params,
                                     symbol_values=parameters, repetitions=1000)
        return output.numpy()[0]

    def draw_circuit(self):
        print(self.circuit)


def train(qaoa, epochs=100):
    loss_history = []
    with tqdm.trange(epochs) as iterator:
        iterator.set_description("QAOA Optimization Loop")
        for epoch in iterator:
            with tf.GradientTape() as tape:
                error = qaoa.model(qaoa.initial_state)
            grads = tape.gradient(error, qaoa.model.trainable_variables)
            qaoa.optimizer.apply_gradients(zip(grads, qaoa.model.trainable_variables))
            error = error.numpy()[0][0]
            loss_history.append(error)
            iterator.set_postfix(error=error)
    return qaoa, loss_history


def evaluate(qaoa: QAOAProblem):
    samples = qaoa.sample_solutions()
    # subsets_as_integers = [int("".join(assignment), 2) for assignment in samples.astype(str)]
    cut_sizes = [nx.algorithms.cuts.cut_size(qaoa_instance.graph, np.where(cut)[0]) for cut in samples]
    return np.mean(cut_sizes), np.max(cut_sizes)


qaoa_instance = QAOAProblem(nx.random_regular_graph(n=6, d=3), p=8)
qaoa_instance, losses = train(qaoa_instance, 1000)

# Print the Learned parameters
print("Learned Parameters", qaoa_instance.model.trainable_variables)
# Plotting the Loss curves
plt.plot(losses)
plt.title("QAOA with TFQ")
plt.xlabel("Iteration")
plt.ylabel("Loss")
plt.show()


true_max_cut = qaoa_instance.solve_complete()
average_qaoa_cut, best_qaoa_cut = evaluate(qaoa_instance)
print("Average Approximation Ratio", average_qaoa_cut / true_max_cut)
print("Best Approximation Ratio", best_qaoa_cut / true_max_cut)

qaoa_instance.draw_circuit()
