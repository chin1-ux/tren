var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });
var stateIndexKey = "__TSR_index";
function createHistory(opts) {
  let location = opts.getLocation();
  const subscribers = /* @__PURE__ */ new Set();
  const notify = /* @__PURE__ */ __name((action) => {
    location = opts.getLocation();
    subscribers.forEach((subscriber) => subscriber({
      location,
      action
    }));
  }, "notify");
  const handleIndexChange = /* @__PURE__ */ __name((action) => {
    if (opts.notifyOnIndexChange ?? true) notify(action);
    else location = opts.getLocation();
  }, "handleIndexChange");
  const tryNavigation = /* @__PURE__ */ __name(async ({ task, navigateOpts, ...actionInfo }) => {
    if (navigateOpts?.ignoreBlocker ?? false) {
      task();
      return;
    }
    const blockers = opts.getBlockers?.() ?? [];
    const isPushOrReplace = actionInfo.type === "PUSH" || actionInfo.type === "REPLACE";
    if (typeof document !== "undefined" && blockers.length && isPushOrReplace) for (const blocker of blockers) {
      const nextLocation = parseHref(actionInfo.path, actionInfo.state);
      if (await blocker.blockerFn({
        currentLocation: location,
        nextLocation,
        action: actionInfo.type
      })) {
        opts.onBlocked?.();
        return;
      }
    }
    task();
  }, "tryNavigation");
  return {
    get location() {
      return location;
    },
    get length() {
      return opts.getLength();
    },
    subscribers,
    subscribe: /* @__PURE__ */ __name((cb) => {
      subscribers.add(cb);
      return () => {
        subscribers.delete(cb);
      };
    }, "subscribe"),
    push: /* @__PURE__ */ __name((path, state, navigateOpts) => {
      const currentIndex = location.state[stateIndexKey];
      state = assignKeyAndIndex(currentIndex + 1, state);
      tryNavigation({
        task: /* @__PURE__ */ __name(() => {
          opts.pushState(path, state);
          notify({ type: "PUSH" });
        }, "task"),
        navigateOpts,
        type: "PUSH",
        path,
        state
      });
    }, "push"),
    replace: /* @__PURE__ */ __name((path, state, navigateOpts) => {
      const currentIndex = location.state[stateIndexKey];
      state = assignKeyAndIndex(currentIndex, state);
      tryNavigation({
        task: /* @__PURE__ */ __name(() => {
          opts.replaceState(path, state);
          notify({ type: "REPLACE" });
        }, "task"),
        navigateOpts,
        type: "REPLACE",
        path,
        state
      });
    }, "replace"),
    go: /* @__PURE__ */ __name((index, navigateOpts) => {
      tryNavigation({
        task: /* @__PURE__ */ __name(() => {
          opts.go(index);
          handleIndexChange({
            type: "GO",
            index
          });
        }, "task"),
        navigateOpts,
        type: "GO"
      });
    }, "go"),
    back: /* @__PURE__ */ __name((navigateOpts) => {
      tryNavigation({
        task: /* @__PURE__ */ __name(() => {
          opts.back(navigateOpts?.ignoreBlocker ?? false);
          handleIndexChange({ type: "BACK" });
        }, "task"),
        navigateOpts,
        type: "BACK"
      });
    }, "back"),
    forward: /* @__PURE__ */ __name((navigateOpts) => {
      tryNavigation({
        task: /* @__PURE__ */ __name(() => {
          opts.forward(navigateOpts?.ignoreBlocker ?? false);
          handleIndexChange({ type: "FORWARD" });
        }, "task"),
        navigateOpts,
        type: "FORWARD"
      });
    }, "forward"),
    canGoBack: /* @__PURE__ */ __name(() => location.state[stateIndexKey] !== 0, "canGoBack"),
    createHref: /* @__PURE__ */ __name((str) => opts.createHref(str), "createHref"),
    block: /* @__PURE__ */ __name((blocker) => {
      if (!opts.setBlockers) return () => {
      };
      const blockers = opts.getBlockers?.() ?? [];
      opts.setBlockers([...blockers, blocker]);
      return () => {
        const blockers2 = opts.getBlockers?.() ?? [];
        opts.setBlockers?.(blockers2.filter((b) => b !== blocker));
      };
    }, "block"),
    flush: /* @__PURE__ */ __name(() => opts.flush?.(), "flush"),
    destroy: /* @__PURE__ */ __name(() => opts.destroy?.(), "destroy"),
    notify
  };
}
__name(createHistory, "createHistory");
function assignKeyAndIndex(index, state) {
  if (!state) state = {};
  const key = createRandomKey();
  return {
    ...state,
    key,
    __TSR_key: key,
    [stateIndexKey]: index
  };
}
__name(assignKeyAndIndex, "assignKeyAndIndex");
function createMemoryHistory(opts = { initialEntries: ["/"] }) {
  const entries = opts.initialEntries;
  let index = opts.initialIndex ? Math.min(Math.max(opts.initialIndex, 0), entries.length - 1) : entries.length - 1;
  const states = entries.map((_entry, index2) => assignKeyAndIndex(index2, void 0));
  const getLocation = /* @__PURE__ */ __name(() => parseHref(entries[index], states[index]), "getLocation");
  let blockers = [];
  const _getBlockers = /* @__PURE__ */ __name(() => blockers, "_getBlockers");
  const _setBlockers = /* @__PURE__ */ __name((newBlockers) => blockers = newBlockers, "_setBlockers");
  return createHistory({
    getLocation,
    getLength: /* @__PURE__ */ __name(() => entries.length, "getLength"),
    pushState: /* @__PURE__ */ __name((path, state) => {
      if (index < entries.length - 1) {
        entries.splice(index + 1);
        states.splice(index + 1);
      }
      states.push(state);
      entries.push(path);
      index = Math.max(entries.length - 1, 0);
    }, "pushState"),
    replaceState: /* @__PURE__ */ __name((path, state) => {
      states[index] = state;
      entries[index] = path;
    }, "replaceState"),
    back: /* @__PURE__ */ __name(() => {
      index = Math.max(index - 1, 0);
    }, "back"),
    forward: /* @__PURE__ */ __name(() => {
      index = Math.min(index + 1, entries.length - 1);
    }, "forward"),
    go: /* @__PURE__ */ __name((n) => {
      index = Math.min(Math.max(index + n, 0), entries.length - 1);
    }, "go"),
    createHref: /* @__PURE__ */ __name((path) => path, "createHref"),
    getBlockers: _getBlockers,
    setBlockers: _setBlockers
  });
}
__name(createMemoryHistory, "createMemoryHistory");
function sanitizePath(path) {
  let sanitized = path.replace(/[\x00-\x1f\x7f]/g, "");
  if (sanitized.startsWith("//")) sanitized = "/" + sanitized.replace(/^\/+/, "");
  return sanitized;
}
__name(sanitizePath, "sanitizePath");
function parseHref(href, state) {
  const sanitizedHref = sanitizePath(href);
  const hashIndex = sanitizedHref.indexOf("#");
  const searchIndex = sanitizedHref.indexOf("?");
  const addedKey = createRandomKey();
  return {
    href: sanitizedHref,
    pathname: sanitizedHref.substring(0, hashIndex > 0 ? searchIndex > 0 ? Math.min(hashIndex, searchIndex) : hashIndex : searchIndex > 0 ? searchIndex : sanitizedHref.length),
    hash: hashIndex > -1 ? sanitizedHref.substring(hashIndex) : "",
    search: searchIndex > -1 ? sanitizedHref.slice(searchIndex, hashIndex === -1 ? void 0 : hashIndex) : "",
    state: state || {
      [stateIndexKey]: 0,
      key: addedKey,
      __TSR_key: addedKey
    }
  };
}
__name(parseHref, "parseHref");
function createRandomKey() {
  return (Math.random() + 1).toString(36).substring(7);
}
__name(createRandomKey, "createRandomKey");
export {
  createMemoryHistory as c,
  parseHref as p
};
