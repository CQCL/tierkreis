
// @ts-check

/**
 * @enum {string}
 */


  /**
 * @typedef {Object} PyNode
 * @property {number} id - The node ID.
 * @property {"Not started" | "Started" | "Finished"} status  - The node name.
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
 * @property {"Not started" | "Started" | "Finished"} status - Node status
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


