/**
 * @typedef {Object} PyNode
 * @property {number | string} id - The node ID.
 * @property {"Not started" | "Started" | "Error" | "Finished"} status  - The node name.
 * @property {string} function_name - The node label..
 */

/**
 * @typedef {Object} PyEdge
 * @property {number | string} from_node - The edge name.
 * @property {string} from_port - The edge arrow
 * @property {number | string} to_node - The edge name.
 * @property {string} to_port - The edge label.
 */

/**
 * @typedef {Object} JSNode
 * @property {number | string} id - The node ID.
 * @property {string} title - The node name.
 * @property {string} label - The node label..
 * @property {string} shape - Node shape.
 * @property {string} color - Node colour.
 * @property {"Not started" | "Started" | "Error" | "Finished"} status - Node status
 */

/**
 * @typedef {Object} JSEdge
 * @property {string} id - The edge ID.
 * @property {number | string} from - The edge name.
 * @property {number | string} to - The edge label..
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
