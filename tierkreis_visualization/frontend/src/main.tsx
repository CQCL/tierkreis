import React from "react";
import ReactDOM from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  type LoaderFunction,
  type Params,
} from "react-router";

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import App from "./App";

import "./index.css";

const queryClient = new QueryClient();

const workflowId: LoaderFunction = ({ params }: { params: Params }) => {
  return { params };
};

const element = (
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);
const router = createBrowserRouter([
  {
    path: "/",
    element: element,
  },
  {
    path: "/:workflowId",
    element: element,
    loader: workflowId,
  },
  {
    path: "*/:workflowId",
    element: element,
    loader: workflowId,
  },
  {
    path: "*",
    element: element,
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
