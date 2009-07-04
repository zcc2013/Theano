import gof #, gof.variable
import numpy #for numeric_grad

from gof.python25 import all
import gof.utils

_msg_retType = 'op.grad(...) returned a non-list'
_msg_badlen = 'op.grad(...) returned wrong number of gradients'

def grad_sources_inputs(sources, graph_inputs):
    """
    A gradient source is a pair (r, g_r), in which r is a variable, and g_r is a
    variable that is a gradient wrt r.

    This function traverses the graph backward from the 'r' sources,
    calling L{Op.grad}(...) when it is provided by an L{Op}, and at least one of the
    outputs of the L{Op} has an associated gradient.

    The L{Op.grad}(...) functions are called as such:
        op.grad( op.inputs[0], grad(op.outputs[0]))

    This function expects the L{Op.grad}(...) function to return the gradient
    expression [variables] associated with the inputs of the L{Op}. The L{Op} should
    return a list of variables corresponding to the gradients in the same order
    as the inputs. If it has a single output it should return a list or tuple
    of length 1.

    For each input wrt to which an L{Op} is not differentiable, it should return
    None instead of a variable instance.

    @type sources: list
    @param sources: gradient sources (explained below)
    @type graph_inputs: list
    @param graph_inputs: variables considered to be constant

    @rtype: dictionary
    @return: dictionary mapping each variable necessary for a source to its gradient.
    """
    gmap = {}
    for (r, g_r) in sources:
        if g_r is not None:
            if r in gmap:
                gmap[r] = gmap[r] + g_r
            else:
                gmap[r] = g_r

    graph_outputs = gof.utils.uniq([r for r,g in sources])

    if graph_inputs is None:
        graph_inputs = gof.graph.inputs(graph_outputs)

    for node in gof.graph.io_toposort(graph_inputs, graph_outputs).__reversed__():
        g_outputs = [gmap.get(o,None) for o in node.outputs]

        #if all output gradients are None, continue
        if all(map(lambda x:x is None, g_outputs)): continue

        output_arg = g_outputs
        input_arg = node.inputs

        try:
            dinputs = [node.inputs[x[0]] for x in node.op.destroy_map.values()]
        except AttributeError:
            dinputs = []

        new_input_arg = []
        for input in input_arg:
            if input in dinputs and hasattr(input, 'copy'):
                new_input_arg.append(input.copy())
            else:
                new_input_arg.append(input)
        input_arg = new_input_arg
        
        #note that this function is not in a try-except block
        # the rationale:
        #  If the op implements grad, then any exception should be passed to the
        #  caller
        #  If the op doesn't implement grad, this entire function should fail.
        #  Other possibilities:
        #    * return a partial back-prop
        #
        op_grad = node.op.grad(input_arg, output_arg)
        if not isinstance(op_grad, (list,tuple)):
            raise ValueError(_msg_retType, node.op)
        g_inputs = op_grad
        assert isinstance(g_inputs, (list, tuple))
        if len(g_inputs) != len(node.inputs):
            raise ValueError(_msg_badlen, 
                    node.op, 
                    len(g_inputs),
                    len(node.inputs))
        for ii, (r, g_r) in enumerate(zip(node.inputs, g_inputs)):
            if g_r and (r.type != g_r.type):
                print 'WARNING: %s.grad returned a different type for input %i: %s vs. %s'%(node.op, ii, r.type, g_r.type)
            if g_r and len(sources) == 1 and sources[0][0].name and r.name:
                g_r.name = "(d%s/d%s)" % (sources[0][0].name, r.name)
            if g_r is not None: 
                if r in gmap:
                    gmap[r] = gmap[r] + g_r
                else:
                    gmap[r] = g_r
    return gmap


