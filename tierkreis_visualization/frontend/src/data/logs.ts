import { URL } from "./constants";

export async function getLogs(workflowId: string, node_location:string) {
    const url = `${URL}/${workflowId}/nodes/${node_location}/logs`
    const data = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/text' } }).then((res)=> res.text());
    return data
}
