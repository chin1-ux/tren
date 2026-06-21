var __defProp = Object.defineProperty;
var __typeError = (msg) => {
  throw TypeError(msg);
};
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });
var __accessCheck = (obj, member, msg) => member.has(obj) || __typeError("Cannot " + msg);
var __privateGet = (obj, member, getter) => (__accessCheck(obj, member, "read from private field"), getter ? getter.call(obj) : member.get(obj));
var __privateAdd = (obj, member, value) => member.has(obj) ? __typeError("Cannot add the same private member more than once") : member instanceof WeakSet ? member.add(obj) : member.set(obj, value);
var __privateSet = (obj, member, value, setter) => (__accessCheck(obj, member, "write to private field"), setter ? setter.call(obj, value) : member.set(obj, value), value);
var __privateMethod = (obj, member, method) => (__accessCheck(obj, member, "access private method"), method);
import { Readable, PassThrough } from "node:stream";
function lazyInherit(target, source, sourceKey) {
  for (const key of [...Object.getOwnPropertyNames(source), ...Object.getOwnPropertySymbols(source)]) {
    if (key === "constructor") continue;
    const targetDesc = Object.getOwnPropertyDescriptor(target, key);
    const desc = Object.getOwnPropertyDescriptor(source, key);
    let modified = false;
    if (desc.get) {
      modified = true;
      desc.get = targetDesc?.get || function() {
        return this[sourceKey][key];
      };
    }
    if (desc.set) {
      modified = true;
      desc.set = targetDesc?.set || function(value) {
        this[sourceKey][key] = value;
      };
    }
    if (!targetDesc?.value && typeof desc.value === "function") {
      modified = true;
      desc.value = function(...args) {
        return this[sourceKey][key](...args);
      };
    }
    if (modified) Object.defineProperty(target, key, desc);
  }
}
__name(lazyInherit, "lazyInherit");
const _needsNormRE = /(?:(?:^|\/)(?:\.|\.\.|%2e|%2e\.|\.%2e|%2e%2e)(?:\/|$))|[\\^\x80-\uffff]/i;
const FastURL = /* @__PURE__ */ (() => {
  var _url, _href, _protocol, _host, _pathname, _search, _searchParams, _pos, _URL_instances, getPos_fn, _a;
  const NativeURL = globalThis.URL;
  const FastURL2 = (_a = class {
    constructor(url) {
      __privateAdd(this, _URL_instances);
      __privateAdd(this, _url);
      __privateAdd(this, _href);
      __privateAdd(this, _protocol);
      __privateAdd(this, _host);
      __privateAdd(this, _pathname);
      __privateAdd(this, _search);
      __privateAdd(this, _searchParams);
      __privateAdd(this, _pos);
      if (typeof url === "string") if (url[0] === "/") __privateSet(this, _href, url);
      else __privateSet(this, _url, new NativeURL(url));
      else if (_needsNormRE.test(url.pathname)) __privateSet(this, _url, new NativeURL(`${url.protocol || "http:"}//${url.host || "localhost"}${url.pathname}${url.search || ""}`));
      else {
        __privateSet(this, _protocol, url.protocol);
        __privateSet(this, _host, url.host);
        __privateSet(this, _pathname, url.pathname);
        __privateSet(this, _search, url.search);
      }
    }
    static [Symbol.hasInstance](val) {
      return val instanceof NativeURL;
    }
    get _url() {
      if (__privateGet(this, _url)) return __privateGet(this, _url);
      __privateSet(this, _url, new NativeURL(this.href));
      __privateSet(this, _href, void 0);
      __privateSet(this, _protocol, void 0);
      __privateSet(this, _host, void 0);
      __privateSet(this, _pathname, void 0);
      __privateSet(this, _search, void 0);
      __privateSet(this, _searchParams, void 0);
      __privateSet(this, _pos, void 0);
      return __privateGet(this, _url);
    }
    get href() {
      if (__privateGet(this, _url)) return __privateGet(this, _url).href;
      if (!__privateGet(this, _href)) __privateSet(this, _href, `${__privateGet(this, _protocol) || "http:"}//${__privateGet(this, _host) || "localhost"}${__privateGet(this, _pathname) || "/"}${__privateGet(this, _search) || ""}`);
      return __privateGet(this, _href);
    }
    get pathname() {
      if (__privateGet(this, _url)) return __privateGet(this, _url).pathname;
      if (__privateGet(this, _pathname) === void 0) {
        const [, pathnameIndex, queryIndex] = __privateMethod(this, _URL_instances, getPos_fn).call(this);
        if (pathnameIndex === -1) return this._url.pathname;
        __privateSet(this, _pathname, this.href.slice(pathnameIndex, queryIndex === -1 ? void 0 : queryIndex));
      }
      return __privateGet(this, _pathname);
    }
    get search() {
      if (__privateGet(this, _url)) return __privateGet(this, _url).search;
      if (__privateGet(this, _search) === void 0) {
        const [, pathnameIndex, queryIndex] = __privateMethod(this, _URL_instances, getPos_fn).call(this);
        if (pathnameIndex === -1) return this._url.search;
        const url = this.href;
        __privateSet(this, _search, queryIndex === -1 || queryIndex === url.length - 1 ? "" : url.slice(queryIndex));
      }
      return __privateGet(this, _search);
    }
    get searchParams() {
      if (__privateGet(this, _url)) return __privateGet(this, _url).searchParams;
      if (!__privateGet(this, _searchParams)) __privateSet(this, _searchParams, new URLSearchParams(this.search));
      return __privateGet(this, _searchParams);
    }
    get protocol() {
      if (__privateGet(this, _url)) return __privateGet(this, _url).protocol;
      if (__privateGet(this, _protocol) === void 0) {
        const [protocolIndex] = __privateMethod(this, _URL_instances, getPos_fn).call(this);
        if (protocolIndex === -1) return this._url.protocol;
        const url = this.href;
        __privateSet(this, _protocol, url.slice(0, protocolIndex + 1));
      }
      return __privateGet(this, _protocol);
    }
    toString() {
      return this.href;
    }
    toJSON() {
      return this.href;
    }
  }, _url = new WeakMap(), _href = new WeakMap(), _protocol = new WeakMap(), _host = new WeakMap(), _pathname = new WeakMap(), _search = new WeakMap(), _searchParams = new WeakMap(), _pos = new WeakMap(), _URL_instances = new WeakSet(), getPos_fn = /* @__PURE__ */ __name(function() {
    if (!__privateGet(this, _pos)) {
      const url = this.href;
      const protoIndex = url.indexOf("://");
      const pathnameIndex = protoIndex === -1 ? -1 : url.indexOf("/", protoIndex + 4);
      const qIndex = pathnameIndex === -1 ? -1 : url.indexOf("?", pathnameIndex);
      __privateSet(this, _pos, [
        protoIndex,
        pathnameIndex,
        qIndex
      ]);
    }
    return __privateGet(this, _pos);
  }, "#getPos"), __name(_a, "URL"), _a);
  lazyInherit(FastURL2.prototype, NativeURL.prototype, "_url");
  Object.setPrototypeOf(FastURL2.prototype, NativeURL.prototype);
  Object.setPrototypeOf(FastURL2, NativeURL);
  return FastURL2;
})();
const NodeResponse = /* @__PURE__ */ (() => {
  var _body, _init, _headers, _response;
  const NativeResponse = globalThis.Response;
  const STATUS_CODES = globalThis.process?.getBuiltinModule?.("node:http")?.STATUS_CODES || {};
  const _NodeResponse = class _NodeResponse {
    constructor(body, init) {
      __privateAdd(this, _body);
      __privateAdd(this, _init);
      __privateAdd(this, _headers);
      __privateAdd(this, _response);
      __privateSet(this, _body, body);
      __privateSet(this, _init, init);
    }
    static [Symbol.hasInstance](val) {
      return val instanceof NativeResponse;
    }
    get status() {
      return __privateGet(this, _response)?.status || __privateGet(this, _init)?.status || 200;
    }
    get statusText() {
      return __privateGet(this, _response)?.statusText || __privateGet(this, _init)?.statusText || STATUS_CODES[this.status] || "";
    }
    get headers() {
      if (__privateGet(this, _response)) return __privateGet(this, _response).headers;
      if (__privateGet(this, _headers)) return __privateGet(this, _headers);
      const initHeaders = __privateGet(this, _init)?.headers;
      return __privateSet(this, _headers, initHeaders instanceof Headers ? initHeaders : new Headers(initHeaders));
    }
    get ok() {
      if (__privateGet(this, _response)) return __privateGet(this, _response).ok;
      const status = this.status;
      return status >= 200 && status < 300;
    }
    get _response() {
      if (__privateGet(this, _response)) return __privateGet(this, _response);
      let body = __privateGet(this, _body);
      if (body && typeof body.pipe === "function" && !(body instanceof Readable)) {
        const stream = new PassThrough();
        body.pipe(stream);
        const abort = body.abort;
        if (abort) stream.once("close", () => abort());
        body = stream;
      }
      __privateSet(this, _response, new NativeResponse(body, __privateGet(this, _headers) ? {
        ...__privateGet(this, _init),
        headers: __privateGet(this, _headers)
      } : __privateGet(this, _init)));
      __privateSet(this, _init, void 0);
      __privateSet(this, _headers, void 0);
      __privateSet(this, _body, void 0);
      return __privateGet(this, _response);
    }
    _toNodeResponse() {
      const status = this.status;
      const statusText = this.statusText;
      let body;
      let contentType;
      let contentLength;
      if (__privateGet(this, _response)) body = __privateGet(this, _response).body;
      else if (__privateGet(this, _body)) if (__privateGet(this, _body) instanceof ReadableStream) body = __privateGet(this, _body);
      else if (typeof __privateGet(this, _body) === "string") {
        body = __privateGet(this, _body);
        contentType = "text/plain; charset=UTF-8";
        contentLength = Buffer.byteLength(__privateGet(this, _body));
      } else if (__privateGet(this, _body) instanceof ArrayBuffer) {
        body = Buffer.from(__privateGet(this, _body));
        contentLength = __privateGet(this, _body).byteLength;
      } else if (__privateGet(this, _body) instanceof Uint8Array) {
        body = __privateGet(this, _body);
        contentLength = __privateGet(this, _body).byteLength;
      } else if (__privateGet(this, _body) instanceof DataView) {
        body = Buffer.from(__privateGet(this, _body).buffer);
        contentLength = __privateGet(this, _body).byteLength;
      } else if (__privateGet(this, _body) instanceof Blob) {
        body = __privateGet(this, _body).stream();
        contentType = __privateGet(this, _body).type;
        contentLength = __privateGet(this, _body).size;
      } else if (typeof __privateGet(this, _body).pipe === "function") body = __privateGet(this, _body);
      else body = this._response.body;
      const headers = [];
      const initHeaders = __privateGet(this, _init)?.headers;
      const headerEntries = __privateGet(this, _response)?.headers || __privateGet(this, _headers) || (initHeaders ? Array.isArray(initHeaders) ? initHeaders : initHeaders?.entries ? initHeaders.entries() : Object.entries(initHeaders).map(([k, v]) => [k.toLowerCase(), v]) : void 0);
      let hasContentTypeHeader;
      let hasContentLength;
      if (headerEntries) for (const [key, value] of headerEntries) {
        if (Array.isArray(value)) for (const v of value) headers.push([key, v]);
        else headers.push([key, value]);
        if (key === "content-type") hasContentTypeHeader = true;
        else if (key === "content-length") hasContentLength = true;
      }
      if (contentType && !hasContentTypeHeader) headers.push(["content-type", contentType]);
      if (contentLength && !hasContentLength) headers.push(["content-length", String(contentLength)]);
      __privateSet(this, _init, void 0);
      __privateSet(this, _headers, void 0);
      __privateSet(this, _response, void 0);
      __privateSet(this, _body, void 0);
      return {
        status,
        statusText,
        headers,
        body
      };
    }
  };
  _body = new WeakMap();
  _init = new WeakMap();
  _headers = new WeakMap();
  _response = new WeakMap();
  __name(_NodeResponse, "NodeResponse");
  let NodeResponse2 = _NodeResponse;
  lazyInherit(NodeResponse2.prototype, NativeResponse.prototype, "_response");
  Object.setPrototypeOf(NodeResponse2, NativeResponse);
  Object.setPrototypeOf(NodeResponse2.prototype, NativeResponse.prototype);
  return NodeResponse2;
})();
export {
  FastURL as F,
  NodeResponse as N
};
