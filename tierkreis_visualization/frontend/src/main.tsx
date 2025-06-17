import React from "react";
import ReactDOM from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  type LoaderFunction,
  type Params,
} from "react-router";
import App from "./App";

import "./index.css";

const workflowId: LoaderFunction = ({ params }: { params: Params }) => {
  return { params };
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
  },
  {
    path: "/:workflowId",
    element: <App />,
    loader: workflowId,
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
