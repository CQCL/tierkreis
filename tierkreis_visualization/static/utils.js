

const neutrals = {
    50 :"#fafafa",
    100 :"#f4f4f5",
    200 :"#e4e4e7",
    300 :"#d4d4d8",
    400 :"#a1a1aa",
    500 :"#71717a",
    600 :"#52525b",
    700 :"#3f3f46",
    800: "#27272a",
    900 :"#18181b",
    950 :"#09090b",
}

const colors = {
   green: {
    primary: "#bbf7d0"
   },
   red: {
    primary: "#fca5a5"
   },
   amber: {
    primary: "#fde68a"
   }
}


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
        label: py_node.function_name,
        status: py_node.status,
        color: {
            "Not started": neutrals[200],
            "Started": colors.amber.primary,
            "Finished": colors.green.primary,
        }[py_node.status],
        shape: "box",
    }
}




