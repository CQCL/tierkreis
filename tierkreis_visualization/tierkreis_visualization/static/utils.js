// @ts-check

/**
 * Creates a JSEdge from a PyEdge model.
 * @param {PyEdge} py_edge
 * @returns {JSEdge}
 */
function createJSEdge(py_edge) {
    return {
        id: `${py_edge.from_port}->${py_edge.to_port}:${py_edge.from_node}->${py_edge.to_node}`,
       from: py_edge.from_node,
       to: py_edge.to_node,
       title: `${py_edge.from_port}->${py_edge.to_port}`,
       label: `${py_edge.from_port}->${py_edge.to_port}`,
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
        label: py_node.function_name,
        status: py_node.status,
        color: {
            "Not started": colors.neutral[0],
            "Started": colors.amber.primary,
            "Error": colors.red.primary,
            "Finished": colors.green.primary,
        }[py_node.status],
        shape: ["input", "output"].includes(py_node.function_name) ? "ellipse" : "box",
    }
}
