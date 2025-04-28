
// @ts-check

/**
 * @enum {string}
 */
const NodeStatus = {
    NOT_STARTED : "Not started",
    STARTED : "Started",
    FINISHED : "Finished"
  };

  /**
 * @typedef {Object} PyNode
 * @property {number} id - The node ID.
 * @property {NodeStatus} status  - The node name.
 * @property {string} function_name - The node label..
 */

/**
 * @typedef {Object} PyEdge
 * @property {number} from_node - The edge name.
 * @property {string} from_port - The edge arrow
 * @property {number} to_node - The edge name.
 * @property {string} to_port - The edge label.
 */


/**
 * @typedef {Object} JSNode
 * @property {number} id - The node ID.
 * @property {string} title - The node name.
 * @property {string} label - The node label..
 * @property {string} shape - Node shape.
 * @property {NodeStatus} status - Node status
 */


/**
 * @typedef {Object} JSEdge
 * @property {string} id - The edge ID.
 * @property {number} from - The edge name.
 * @property {number} to - The edge label..
 * @property {string} title - The edge name.
 * @property {string} label - Node shape.
 * @property {string} arrows - The edge arrow
 */

/**
 * @typedef {Object} JSGraph
 * @property {JSNode[]} nodes - The edge ID.
 * @property {JSEdge[]} edges - The edge name.
 */

/**
 * @typedef {Object} PyGraph
 * @property {PyNode[]} nodes - The edge ID.
 * @property {PyEdge[]} edges - The edge name.
 */





/**
 * @typedef {any} vis
 * @global
 */

/**
 * @typedef {any} network
 * @global
 */



/**
 * Creates a JSEdge from a PyEdge model.
 * @param {PyEdge} py_edge
 * @returns {JSEdge}
 */
function createJSEdge(py_edge) {
    return {
        id: `${py_edge.from_port}->${py_edge.to_port}:${py_edge.from_node}->${py_edge.to_node}`,
       from: py_edge.from_node,
       to:py_edge.to_node,
       title:`${py_edge.from_port}->${py_edge.to_port}`,
       label: py_edge.to_port,
        arrows: "to"
    }
}

/**
  * Creates a JSNode from a PyNode model.
 * @param {PyNode} py_node
 * @returns {JSNode} A newly created user.
 */
function createJSNode(py_node) {
    return {
        id: py_node.id,
        title: `Function name: ${py_node.function_name}\nStatus: ${py_node.status}`,
        label:py_node.function_name,
        status: py_node.status,
        shape:"box",
    }
}

