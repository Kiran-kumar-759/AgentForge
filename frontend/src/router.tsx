import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api/client";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

export const getRouter = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: (count, err) => count < 2 && !(err instanceof ApiError && (err.kind === "config" || err.kind === "not_found" || err.kind === "malformed")),
        refetchOnWindowFocus: false,
      },
    },
  });

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
