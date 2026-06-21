var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });
import { a as ai, r as re } from "./seroval.mjs";
var n = {}, P = /* @__PURE__ */ __name((e) => new ReadableStream({ start: /* @__PURE__ */ __name((r) => {
  e.on({ next: /* @__PURE__ */ __name((a) => {
    try {
      r.enqueue(a);
    } catch (t) {
    }
  }, "next"), throw: /* @__PURE__ */ __name((a) => {
    r.error(a);
  }, "throw"), return: /* @__PURE__ */ __name(() => {
    try {
      r.close();
    } catch (a) {
    }
  }, "return") });
}, "start") }), "P"), x = ai({ tag: "seroval-plugins/web/ReadableStreamFactory", test(e) {
  return e === n;
}, parse: { sync() {
  return n;
}, async async() {
  return await Promise.resolve(n);
}, stream() {
  return n;
} }, serialize() {
  return P.toString();
}, deserialize() {
  return n;
} });
function w(e) {
  let r = re(), a = e.getReader();
  async function t() {
    try {
      let s = await a.read();
      s.done ? r.return(s.value) : (r.next(s.value), await t());
    } catch (s) {
      r.throw(s);
    }
  }
  __name(t, "t");
  return t().catch(() => {
  }), r;
}
__name(w, "w");
var ee = ai({ tag: "seroval/plugins/web/ReadableStream", extends: [x], test(e) {
  return typeof ReadableStream == "undefined" ? false : e instanceof ReadableStream;
}, parse: { sync(e, r) {
  return { factory: r.parse(n), stream: r.parse(re()) };
}, async async(e, r) {
  return { factory: await r.parse(n), stream: await r.parse(w(e)) };
}, stream(e, r) {
  return { factory: r.parse(n), stream: r.parse(w(e)) };
} }, serialize(e, r) {
  return "(" + r.serialize(e.factory) + ")(" + r.serialize(e.stream) + ")";
}, deserialize(e, r) {
  let a = r.deserialize(e.stream);
  return P(a);
} }), p = ee;
export {
  p
};
