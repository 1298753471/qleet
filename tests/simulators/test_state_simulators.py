import numpy as np
import sympy
import cirq
import qiskit

import qleet


def test_cirq_simulator():
    params = sympy.symbols("param:%d" % 2)
    cirq_circuit = cirq.Circuit(
        [
            cirq.rx(params[0]).on(cirq.NamedQubit("q_0")),
            cirq.CX(cirq.NamedQubit("q_0"), cirq.NamedQubit("q_1")),
            cirq.rx(params[1]).on(cirq.NamedQubit("q_1")),
        ]
    )
    cirq_descriptor = qleet.utils.circuit.CircuitDescriptor(
        circuit=cirq_circuit, params=params, cost_function=cirq.PauliSum()
    )
    params = {p: np.random.random() * 2 * np.pi for p in cirq_descriptor.parameters}


def test_qiskit_simulator():
    params = [qiskit.circuit.Parameter(r"$θ_1$"), qiskit.circuit.Parameter(r"$θ_2$")]
    qiskit_circuit = qiskit.QuantumCircuit(2)
    qiskit_circuit.rx(params[0], 0)
    qiskit_circuit.cx(0, 1)
    qiskit_circuit.rx(params[1], 1)
    qiskit_descriptor = qleet.utils.circuit.CircuitDescriptor(
        circuit=qiskit_circuit, params=params, cost_function=cirq.PauliSum()
    )

    simulator = qleet.simulators.state_simulators.StateSimulator(qiskit_descriptor)
    params = {p: np.random.random() * 2 * np.pi for p in qiskit_descriptor.parameters}
    state_vector = simulator.simulate(params)
    assert isinstance(state_vector, np.ndarray), "State vector should be a numpy array"
    assert (
        len(state_vector.shape) == 1 and state_vector.shape[0] == 4
    ), "State vector is not of right shape"
