from ...operations.operation_base import Operation
from ...tensor_base import Tensor
from numbers import Integral
import numpy as np

from numba import njit


@njit
def _dot_tanh_accum(x, W):
    for n in range(len(x) - 1):
        x[n + 1] += np.dot(x[n], W)
        x[n + 1] = np.tanh(x[n + 1])


class RecurrentUnit(Operation):
    """ Defines a basic recurrent unit for a RNN.

        This unit operates on a sequence of data {X_j | (0 <= j <= T - 1)}, producing
        a sequence of "hidden descriptors": {S_i | (0 <= i <= T}}, via the trainable parameters
        U and W

                                S_{t} = tanh(U X_{t-1} + W S_{t-1})

        For a language model, S_{t} is traditionally mapped to a prediction of X_t via: softmax(V S_t),
        where V is yet another trainable parameter (not built into the recurrent unit)."""

    def __call__(self, X, U, W, s0=None, bp_lim=None, backprop_s=False):
        """ Performs a forward pass of sequential data through a simple RNN layer, returning
            the 'hidden-descriptors' arrived at by utilizing the trainable parameters U and V:

                                S_{t} = tanh(U X_{t-1} + W S_{t-1})

            Parameters
            ----------
            X : mygrad.Tensor, shape=(T, N, C)
               The sequential data to be passed forward.

            U : mygrad.Tensor, shape=(D, C)
               The weights used to map sequential data to its hidden-descriptor representation

            W : mygrad.Tensor, shape=(D, D)
                The weights used to map a hidden-descriptor to a hidden-descriptor.

            s0 : Optional[mygrad.Tensor, numpy.ndarray], shape=(N, D)
                The 'seed' hidden descriptors to feed into the RNN. If None, a Tensor
                of zeros of shape (N, D) is created.

            bp_lim : Optional[int]
                The (non-zero) limit of the number of back propagations through time are
                performed

            backprop_s : bool, (default=True)
                If False, backpropagation will not be carried through the hidden-descriptors through
                this RNN.

            Returns
            -------
            mygrad.Tensor
                The sequence of 'hidden-descriptors' produced by the forward pass of the RNN."""
        if bp_lim is not None:
            assert isinstance(bp_lim, Integral) and bp_lim > 0
        self.bp_lim = bp_lim if bp_lim is not None else len(X)
        self.backprop_s = backprop_s

        self.X = X
        self.U = U
        self.W = W
        self._hidden_seq = []

        seq = self.X.data
        out = np.zeros((seq.shape[0] + 1, seq.shape[1], self.U.shape[-1]))

        if s0 is not None:
            out[0] = s0.data if isinstance(s0, Tensor) else s0

        np.dot(seq, self.U.data, out=out[1:])
        _dot_tanh_accum(out, self.W.data)

        self._hidden_seq = Tensor(out, _creator=self)

        return self._hidden_seq.data

    def backward(self, grad, seq_index=None):
        if self.U.constant and self.W.constant and self.X.constant and self.backprop_s:
            return None

        s = self._hidden_seq

        dst_dft = (1 - s.data ** 2)

        if self.backprop_s:
            dLt_dst = grad * 1  # dLt / dst
            old_dst = np.zeros_like(grad)

        dLt_dft = grad * dst_dft  # dLt / dst
        old_dft = np.zeros_like(grad)

        if self.backprop_s:
            for i in range(min(s.shape[0] - 1, self.bp_lim)):
                dst = dst_dft[2:len(grad) - i] * (dLt_dst[2:len(grad) - i] - old_dst[2:len(grad) - i])  # ds_t+1 / df_t
                old_dst = np.copy(dLt_dst)
                dLt_dst[1:len(grad) - (i + 1)] += np.dot(dst, self.W.data.T)  # ds_t+1 / ds_t

        for i in range(min(s.shape[0] - 1, self.bp_lim)):
            dft = dLt_dft[2:len(grad) - i] - old_dft[2:len(grad) - i]
            old_dft = np.copy(dLt_dft)
            dLt_dft[1:len(grad) - (i + 1)] += dst_dft[1:len(grad) - (i + 1)] * np.dot(dft, self.W.data.T)

        if self.backprop_s:
            self._hidden_seq.grad = dLt_dst
        if not self.U.constant:
            self.U.backward(np.einsum("ijk, ijl -> kl", self.X.data, dLt_dft[1:]))
        if not self.W.constant:
            self.W.backward(np.einsum("ijk, ijl -> kl", s.data[:-1], dLt_dft[1:]))
<<<<<<< HEAD
    def no_recursion_null_grad(self):
        firstguy=True
        for attr in self.__dict__:
            var = getattr(self, attr)
            if hasattr(var, "grad"):
                    var.grad=None
            if hasattr(var, "_ops"):
                    var._ops = []
        
        
    def backward_2(self, grad, seq_index=None):
        if self.U.constant and self.W.constant and self._input_seq.constant:
            return None

        s = self._hidden_seq

        dsdf = (1 - s.data ** 2)
        grad = grad * dsdf  # dLt / dst
        old_grad = np.zeros_like(grad)

        for i in range(min(s.shape[0] - 1, self.bp_lim)):
            dt = grad[2:len(grad) - i] - old_grad[2:len(grad) - i]  # ds_t+1 / df_t
            old_grad = np.copy(grad)
            grad[1:len(grad) - (i + 1)] += dsdf[1:len(grad) - (i + 1)] * np.dot(dt, self.W.data.T)  # ds_t+1 / ds_t

        if not self.U.constant:
            self.U.backward(np.einsum("ijk, ijl -> kl", self._input_seq.data, grad[1:]))
        if not self.W.constant:
            self.W.backward(np.einsum("ijk, ijl -> kl", s.data[:-1], grad[1:]))



class OldRecurrentUnit(Operation):
    def __init__(self, U, W, V, bp_lim):
        self.U = U
        self.W = W
        self.V = V
        self.bp_lim = bp_lim

        self._input_seq = None
        self._hidden_seq = []

        self.bp_cnt = 0

    def __call__(self, seq, s0=None):

        if self._input_seq is None:
            self._input_seq = seq
        else:
            self._input_seq = np.vstack((self._input_seq, seq))

        out = np.zeros((seq.shape[0] + 1, seq.shape[1], self.U.shape[-1]))

        if self._hidden_seq:
            out[0] = self._hidden_seq[-1].data
        elif s0 is not None:
            out[0] = s0 if isinstance(s0, Tensor) else s0

        np.dot(seq, self.U.data, out=out[1:])
        for n, s_prev in enumerate(out[:-1]):
            out[n + 1] += s_prev.dot(self.W.data)
            out[n + 1] = np.tanh(out[n + 1])

        if not self._hidden_seq:
            self._hidden_seq = [Tensor(out[0], _creator=self, _seq_index=0)]

        self._hidden_seq += [Tensor(s, _creator=self, _seq_index=(n + len(self._hidden_seq)))
                             for n, s in enumerate(out[1:])]
        return self._hidden_seq

    def backward(self, grad, seq_index=None):
        """ o = UX_t + WS_{t-1}
            S_{t} = tanh(o)"""

        self.bp_cnt += 1

        s = self._hidden_seq[seq_index]
        s_prev = self._hidden_seq[seq_index - 1]
        x = self._input_seq[seq_index - 1]

        dLdo = grad * (1 - s.data ** 2)
        self.U.backward(np.dot(x.T, dLdo))
        self.W.backward(np.dot(s_prev.data.T, dLdo))

        s.grad = None
        if self.bp_cnt == self.bp_lim or seq_index == 1:
            self.bp_cnt = 0
        else:
            s_prev.grad = None
            s_prev.backward(np.dot(dLdo, self.W.data.T))








=======
        if not self.X.constant:
            self.X.backward(np.dot(dLt_dft[1:], self.U.data.T))


def simple_RNN(X, U, W, s0=None, bp_lim=None, backprop_s=False):
    """ Performs a forward pass of sequential data through a simple RNN layer, returning
        the 'hidden-descriptors' arrived at by utilizing the trainable parameters U and V:

                            S_{t} = tanh(U X_{t-1} + W S_{t-1})

        Parameters
        ----------
        X : mygrad.Tensor, shape=(T, N, C)
           The sequential data to be passed forward.

        U : mygrad.Tensor, shape=(D, C)
           The weights used to map sequential data to its hidden-descriptor representation

        W : mygrad.Tensor, shape=(D, D)
            The weights used to map a hidden-descriptor to a hidden-descriptor.

        s0 : Optional[mygrad.Tensor, numpy.ndarray], shape=(N, D)
            The 'seed' hidden descriptors to feed into the RNN. If None, a Tensor
            of zeros of shape (N, D) is created.

        bp_lim : Optional[int]
            The (non-zero) limit of the number of back propagations through time are
            performed

        backprop_s : bool, (default=False)
            If False, backpropagation will not be carried through the hidden-descriptors of
            this RNN. Backpropagation through X, U, and W will still occur, granted that
            these are non-constant Tensors.

        Returns
        -------
        mygrad.Tensor
            The sequence of 'hidden-descriptors' produced by the forward pass of the RNN.

        Notes
        -----
        T : Sequence length
        N : Batch size
        C : Length of single datum
        D : Length of 'hidden' descriptor"""
    s = Tensor._op(RecurrentUnit, X, U, W, op_kwargs=dict(s0=s0, bp_lim=bp_lim, backprop_s=backprop_s))
    s.creator._hidden_seq = s
    return s
>>>>>>> master
