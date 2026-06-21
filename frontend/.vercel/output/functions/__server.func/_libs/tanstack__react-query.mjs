var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });
import { r as reactExports, j as jsxRuntimeExports } from "./react.mjs";
import { s as shouldThrowError, n as notifyManager, a as noop, e as environmentManager, Q as QueryObserver } from "./tanstack__query-core.mjs";
var QueryClientContext = reactExports.createContext(
  void 0
);
var useQueryClient = /* @__PURE__ */ __name((queryClient) => {
  const client = reactExports.useContext(QueryClientContext);
  if (!client) {
    throw new Error("No QueryClient set, use QueryClientProvider to set one");
  }
  return client;
}, "useQueryClient");
var QueryClientProvider = /* @__PURE__ */ __name(({
  client,
  children
}) => {
  reactExports.useEffect(() => {
    client.mount();
    return () => {
      client.unmount();
    };
  }, [client]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx(QueryClientContext.Provider, { value: client, children });
}, "QueryClientProvider");
var IsRestoringContext = reactExports.createContext(false);
var useIsRestoring = /* @__PURE__ */ __name(() => reactExports.useContext(IsRestoringContext), "useIsRestoring");
IsRestoringContext.Provider;
function createValue() {
  let isReset = false;
  return {
    clearReset: /* @__PURE__ */ __name(() => {
      isReset = false;
    }, "clearReset"),
    reset: /* @__PURE__ */ __name(() => {
      isReset = true;
    }, "reset"),
    isReset: /* @__PURE__ */ __name(() => {
      return isReset;
    }, "isReset")
  };
}
__name(createValue, "createValue");
var QueryErrorResetBoundaryContext = reactExports.createContext(createValue());
var useQueryErrorResetBoundary = /* @__PURE__ */ __name(() => reactExports.useContext(QueryErrorResetBoundaryContext), "useQueryErrorResetBoundary");
var ensurePreventErrorBoundaryRetry = /* @__PURE__ */ __name((options, errorResetBoundary, query) => {
  const throwOnError = query?.state.error && typeof options.throwOnError === "function" ? shouldThrowError(options.throwOnError, [query.state.error, query]) : options.throwOnError;
  if (options.suspense || options.experimental_prefetchInRender || throwOnError) {
    if (!errorResetBoundary.isReset()) {
      options.retryOnMount = false;
    }
  }
}, "ensurePreventErrorBoundaryRetry");
var useClearResetErrorBoundary = /* @__PURE__ */ __name((errorResetBoundary) => {
  reactExports.useEffect(() => {
    errorResetBoundary.clearReset();
  }, [errorResetBoundary]);
}, "useClearResetErrorBoundary");
var getHasError = /* @__PURE__ */ __name(({
  result,
  errorResetBoundary,
  throwOnError,
  query,
  suspense
}) => {
  return result.isError && !errorResetBoundary.isReset() && !result.isFetching && query && (suspense && result.data === void 0 || shouldThrowError(throwOnError, [result.error, query]));
}, "getHasError");
var ensureSuspenseTimers = /* @__PURE__ */ __name((defaultedOptions) => {
  if (defaultedOptions.suspense) {
    const MIN_SUSPENSE_TIME_MS = 1e3;
    const clamp = /* @__PURE__ */ __name((value) => value === "static" ? value : Math.max(value ?? MIN_SUSPENSE_TIME_MS, MIN_SUSPENSE_TIME_MS), "clamp");
    const originalStaleTime = defaultedOptions.staleTime;
    defaultedOptions.staleTime = typeof originalStaleTime === "function" ? (...args) => clamp(originalStaleTime(...args)) : clamp(originalStaleTime);
    if (typeof defaultedOptions.gcTime === "number") {
      defaultedOptions.gcTime = Math.max(
        defaultedOptions.gcTime,
        MIN_SUSPENSE_TIME_MS
      );
    }
  }
}, "ensureSuspenseTimers");
var willFetch = /* @__PURE__ */ __name((result, isRestoring) => result.isLoading && result.isFetching && !isRestoring, "willFetch");
var shouldSuspend = /* @__PURE__ */ __name((defaultedOptions, result) => defaultedOptions?.suspense && result.isPending, "shouldSuspend");
var fetchOptimistic = /* @__PURE__ */ __name((defaultedOptions, observer, errorResetBoundary) => observer.fetchOptimistic(defaultedOptions).catch(() => {
  errorResetBoundary.clearReset();
}), "fetchOptimistic");
function useBaseQuery(options, Observer, queryClient) {
  const isRestoring = useIsRestoring();
  const errorResetBoundary = useQueryErrorResetBoundary();
  const client = useQueryClient();
  const defaultedOptions = client.defaultQueryOptions(options);
  client.getDefaultOptions().queries?._experimental_beforeQuery?.(
    defaultedOptions
  );
  const query = client.getQueryCache().get(defaultedOptions.queryHash);
  const subscribed = options.subscribed !== false;
  defaultedOptions._optimisticResults = isRestoring ? "isRestoring" : subscribed ? "optimistic" : void 0;
  ensureSuspenseTimers(defaultedOptions);
  ensurePreventErrorBoundaryRetry(defaultedOptions, errorResetBoundary, query);
  useClearResetErrorBoundary(errorResetBoundary);
  const isNewCacheEntry = !client.getQueryCache().get(defaultedOptions.queryHash);
  const [observer] = reactExports.useState(
    () => new Observer(
      client,
      defaultedOptions
    )
  );
  const result = observer.getOptimisticResult(defaultedOptions);
  const shouldSubscribe = !isRestoring && subscribed;
  reactExports.useSyncExternalStore(
    reactExports.useCallback(
      (onStoreChange) => {
        const unsubscribe = shouldSubscribe ? observer.subscribe(notifyManager.batchCalls(onStoreChange)) : noop;
        observer.updateResult();
        return unsubscribe;
      },
      [observer, shouldSubscribe]
    ),
    () => observer.getCurrentResult(),
    () => observer.getCurrentResult()
  );
  reactExports.useEffect(() => {
    observer.setOptions(defaultedOptions);
  }, [defaultedOptions, observer]);
  if (shouldSuspend(defaultedOptions, result)) {
    throw fetchOptimistic(defaultedOptions, observer, errorResetBoundary);
  }
  if (getHasError({
    result,
    errorResetBoundary,
    throwOnError: defaultedOptions.throwOnError,
    query,
    suspense: defaultedOptions.suspense
  })) {
    throw result.error;
  }
  client.getDefaultOptions().queries?._experimental_afterQuery?.(
    defaultedOptions,
    result
  );
  if (defaultedOptions.experimental_prefetchInRender && !environmentManager.isServer() && willFetch(result, isRestoring)) {
    const promise = isNewCacheEntry ? (
      // Fetch immediately on render in order to ensure `.promise` is resolved even if the component is unmounted
      fetchOptimistic(defaultedOptions, observer, errorResetBoundary)
    ) : (
      // subscribe to the "cache promise" so that we can finalize the currentThenable once data comes in
      query?.promise
    );
    promise?.catch(noop).finally(() => {
      observer.updateResult();
    });
  }
  return !defaultedOptions.notifyOnChangeProps ? observer.trackResult(result) : result;
}
__name(useBaseQuery, "useBaseQuery");
function useQuery(options, queryClient) {
  return useBaseQuery(options, QueryObserver);
}
__name(useQuery, "useQuery");
export {
  QueryClientProvider as Q,
  useQuery as u
};
