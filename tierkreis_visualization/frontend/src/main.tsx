import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { Suspense } from "react";
import ReactDOM from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  type LoaderFunction,
  type Params,
} from "react-router";

import App from "./App";

import { ReactFlowProvider } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./index.css";
import ErrorPage from "./error";

const queryClient = new QueryClient();

const workflowId: LoaderFunction = ({ params }: { params: Params }) => {
  return { params };
};

const element = (
  <QueryClientProvider client={queryClient}>
    <Suspense fallback="Loading...">
      <ReactFlowProvider>
        <App />
      </ReactFlowProvider>
    </Suspense>
  </QueryClientProvider>
);
const router = createBrowserRouter([
  {
    path: "/",
    element: element,
    errorElement: <ErrorPage></ErrorPage>,
  },
  {
    path: "/:workflowId",
    element: element,
    loader: workflowId,
    errorElement: <ErrorPage></ErrorPage>,
  },
  {
    path: "*/:workflowId",
    element: element,
    loader: workflowId,
    errorElement: <ErrorPage></ErrorPage>,
  },
  {
    path: "*",
    element: element,
    errorElement: <ErrorPage></ErrorPage>,
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
