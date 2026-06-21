var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });
var _a2, _b, _c, _d, _e2, _f, _g, _h, _i, _j, _k, _l, _m, _n2, _o2, _p, _q, _r2;
var M = ((i) => (i[i.AggregateError = 1] = "AggregateError", i[i.ArrowFunction = 2] = "ArrowFunction", i[i.ErrorPrototypeStack = 4] = "ErrorPrototypeStack", i[i.ObjectAssign = 8] = "ObjectAssign", i[i.BigIntTypedArray = 16] = "BigIntTypedArray", i[i.RegExp = 32] = "RegExp", i))(M || {});
var v = Symbol.asyncIterator, pr = Symbol.hasInstance, R = Symbol.isConcatSpreadable, C = Symbol.iterator, dr = Symbol.match, gr = Symbol.matchAll, yr = Symbol.replace, Nr = Symbol.search, br = Symbol.species, vr = Symbol.split, Cr = Symbol.toPrimitive, P = Symbol.toStringTag, Ar = Symbol.unscopables;
var tt = { 0: "Symbol.asyncIterator", 1: "Symbol.hasInstance", 2: "Symbol.isConcatSpreadable", 3: "Symbol.iterator", 4: "Symbol.match", 5: "Symbol.matchAll", 6: "Symbol.replace", 7: "Symbol.search", 8: "Symbol.species", 9: "Symbol.split", 10: "Symbol.toPrimitive", 11: "Symbol.toStringTag", 12: "Symbol.unscopables" }, ve = { [v]: 0, [pr]: 1, [R]: 2, [C]: 3, [dr]: 4, [gr]: 5, [yr]: 6, [Nr]: 7, [br]: 8, [vr]: 9, [Cr]: 10, [P]: 11, [Ar]: 12 }, nt = { 0: v, 1: pr, 2: R, 3: C, 4: dr, 5: gr, 6: yr, 7: Nr, 8: br, 9: vr, 10: Cr, 11: P, 12: Ar }, ot = { 2: "!0", 3: "!1", 1: "void 0", 0: "null", 4: "-0", 5: "1/0", 6: "-1/0", 7: "0/0" }, o = void 0, at = { 2: true, 3: false, 1: o, 0: null, 4: -0, 5: Number.POSITIVE_INFINITY, 6: Number.NEGATIVE_INFINITY, 7: Number.NaN };
var Ce = { 0: "Error", 1: "EvalError", 2: "RangeError", 3: "ReferenceError", 4: "SyntaxError", 5: "TypeError", 6: "URIError" }, st = { 0: Error, 1: EvalError, 2: RangeError, 3: ReferenceError, 4: SyntaxError, 5: TypeError, 6: URIError };
function c(e, r, t, n, a, s, i, u, l, g, S, d) {
  return { t: e, i: r, s: t, c: n, m: a, p: s, e: i, a: u, f: l, b: g, o: S, l: d };
}
__name(c, "c");
function B(e) {
  return c(2, o, e, o, o, o, o, o, o, o, o, o);
}
__name(B, "B");
var H = B(2), J = B(3), Ae = B(1), Ee = B(0), it = B(4), ut = B(5), lt = B(6), ct = B(7);
function mn(e) {
  switch (e) {
    case '"':
      return '\\"';
    case "\\":
      return "\\\\";
    case `
`:
      return "\\n";
    case "\r":
      return "\\r";
    case "\b":
      return "\\b";
    case "	":
      return "\\t";
    case "\f":
      return "\\f";
    case "<":
      return "\\x3C";
    case "\u2028":
      return "\\u2028";
    case "\u2029":
      return "\\u2029";
    default:
      return o;
  }
}
__name(mn, "mn");
function y(e) {
  let r = "", t = 0, n;
  for (let a = 0, s = e.length; a < s; a++) n = mn(e[a]), n && (r += e.slice(t, a) + n, t = a + 1);
  return t === 0 ? r = e : r += e.slice(t), r;
}
__name(y, "y");
function pn(e) {
  switch (e) {
    case "\\\\":
      return "\\";
    case '\\"':
      return '"';
    case "\\n":
      return `
`;
    case "\\r":
      return "\r";
    case "\\b":
      return "\b";
    case "\\t":
      return "	";
    case "\\f":
      return "\f";
    case "\\x3C":
      return "<";
    case "\\u2028":
      return "\u2028";
    case "\\u2029":
      return "\u2029";
    default:
      return e;
  }
}
__name(pn, "pn");
function D(e) {
  return e.replace(/(\\\\|\\"|\\n|\\r|\\b|\\t|\\f|\\u2028|\\u2029|\\x3C)/g, pn);
}
__name(D, "D");
var L = "__SEROVAL_REFS__", le = "$R", Ie = `self.${le}`;
function dn(e) {
  return e == null ? `${Ie}=${Ie}||[]` : `(${Ie}=${Ie}||{})["${y(e)}"]=[]`;
}
__name(dn, "dn");
var Er = /* @__PURE__ */ new Map(), U = /* @__PURE__ */ new Map();
function Ir(e) {
  return Er.has(e);
}
__name(Ir, "Ir");
function yn(e) {
  return U.has(e);
}
__name(yn, "yn");
function ft(e) {
  if (Ir(e)) return Er.get(e);
  throw new Re(e);
}
__name(ft, "ft");
function St(e) {
  if (yn(e)) return U.get(e);
  throw new Pe(e);
}
__name(St, "St");
typeof globalThis != "undefined" ? Object.defineProperty(globalThis, L, { value: U, configurable: true, writable: false, enumerable: false }) : typeof window != "undefined" ? Object.defineProperty(window, L, { value: U, configurable: true, writable: false, enumerable: false }) : typeof self != "undefined" ? Object.defineProperty(self, L, { value: U, configurable: true, writable: false, enumerable: false }) : typeof global != "undefined" && Object.defineProperty(global, L, { value: U, configurable: true, writable: false, enumerable: false });
function xe(e) {
  return e instanceof EvalError ? 1 : e instanceof RangeError ? 2 : e instanceof ReferenceError ? 3 : e instanceof SyntaxError ? 4 : e instanceof TypeError ? 5 : e instanceof URIError ? 6 : 0;
}
__name(xe, "xe");
function Nn(e) {
  let r = Ce[xe(e)];
  return e.name !== r ? { name: e.name } : e.constructor.name !== r ? { name: e.constructor.name } : {};
}
__name(Nn, "Nn");
function Z(e, r) {
  let t = Nn(e), n = Object.getOwnPropertyNames(e);
  for (let a = 0, s = n.length, i; a < s; a++) i = n[a], i !== "name" && i !== "message" && (i === "stack" ? r & 4 && (t = t || {}, t[i] = e[i]) : (t = t || {}, t[i] = e[i]));
  return t;
}
__name(Z, "Z");
function Te(e) {
  return Object.isFrozen(e) ? 3 : Object.isSealed(e) ? 2 : Object.isExtensible(e) ? 0 : 1;
}
__name(Te, "Te");
function Oe(e) {
  switch (e) {
    case Number.POSITIVE_INFINITY:
      return ut;
    case Number.NEGATIVE_INFINITY:
      return lt;
  }
  return e !== e ? ct : Object.is(e, -0) ? it : c(0, o, e, o, o, o, o, o, o, o, o, o);
}
__name(Oe, "Oe");
function $(e) {
  return c(1, o, y(e), o, o, o, o, o, o, o, o, o);
}
__name($, "$");
function we(e) {
  return c(3, o, "" + e, o, o, o, o, o, o, o, o, o);
}
__name(we, "we");
function pt(e) {
  return c(4, e, o, o, o, o, o, o, o, o, o, o);
}
__name(pt, "pt");
function he(e, r) {
  let t = r.valueOf();
  return c(5, e, t !== t ? "" : r.toISOString(), o, o, o, o, o, o, o, o, o);
}
__name(he, "he");
function ze(e, r) {
  return c(6, e, o, y(r.source), r.flags, o, o, o, o, o, o, o);
}
__name(ze, "ze");
function dt(e, r) {
  return c(17, e, ve[r], o, o, o, o, o, o, o, o, o);
}
__name(dt, "dt");
function gt(e, r) {
  return c(18, e, y(ft(r)), o, o, o, o, o, o, o, o, o);
}
__name(gt, "gt");
function ce(e, r, t) {
  return c(25, e, t, y(r), o, o, o, o, o, o, o, o);
}
__name(ce, "ce");
function _e(e, r, t) {
  return c(9, e, o, o, o, o, o, t, o, o, Te(r), o);
}
__name(_e, "_e");
function ke(e, r) {
  return c(21, e, o, o, o, o, o, o, r, o, o, o);
}
__name(ke, "ke");
function De(e, r, t) {
  return c(15, e, o, r.constructor.name, o, o, o, o, t, r.byteOffset, o, r.length);
}
__name(De, "De");
function Fe(e, r, t) {
  return c(16, e, o, r.constructor.name, o, o, o, o, t, r.byteOffset, o, r.byteLength);
}
__name(Fe, "Fe");
function Be(e, r, t) {
  return c(20, e, o, o, o, o, o, o, t, r.byteOffset, o, r.byteLength);
}
__name(Be, "Be");
function Ve(e, r, t) {
  return c(13, e, xe(r), o, y(r.message), t, o, o, o, o, o, o);
}
__name(Ve, "Ve");
function Me(e, r, t) {
  return c(14, e, xe(r), o, y(r.message), t, o, o, o, o, o, o);
}
__name(Me, "Me");
function Le(e, r) {
  return c(7, e, o, o, o, o, o, r, o, o, o, o);
}
__name(Le, "Le");
function Ue(e, r) {
  return c(28, o, o, o, o, o, o, [e, r], o, o, o, o);
}
__name(Ue, "Ue");
function je(e, r) {
  return c(30, o, o, o, o, o, o, [e, r], o, o, o, o);
}
__name(je, "je");
function Ye(e, r, t) {
  return c(31, e, o, o, o, o, o, t, r, o, o, o);
}
__name(Ye, "Ye");
function qe(e, r) {
  return c(32, e, o, o, o, o, o, o, r, o, o, o);
}
__name(qe, "qe");
function We(e, r) {
  return c(33, e, o, o, o, o, o, o, r, o, o, o);
}
__name(We, "We");
function Ge(e, r) {
  return c(34, e, o, o, o, o, o, o, r, o, o, o);
}
__name(Ge, "Ge");
function Ke(e, r, t, n) {
  return c(35, e, t, o, o, o, o, r, o, o, o, n);
}
__name(Ke, "Ke");
var bn = { parsing: 1, serialization: 2, deserialization: 3 };
function vn(e) {
  return `Seroval Error (step: ${bn[e]})`;
}
__name(vn, "vn");
var Cn = /* @__PURE__ */ __name((e, r) => vn(e), "Cn"), fe = (_a2 = class extends Error {
  constructor(t, n) {
    super(Cn(t));
    this.cause = n;
  }
}, __name(_a2, "fe"), _a2), z = (_b = class extends fe {
  constructor(r) {
    super("parsing", r);
  }
}, __name(_b, "z"), _b), He = (_c = class extends fe {
  constructor(r) {
    super("deserialization", r);
  }
}, __name(_c, "He"), _c);
function _(e) {
  return `Seroval Error (specific: ${e})`;
}
__name(_, "_");
var x = (_d = class extends Error {
  constructor(t) {
    super(_(1));
    this.value = t;
  }
}, __name(_d, "x"), _d), h = (_e2 = class extends Error {
  constructor(r) {
    super(_(2));
  }
}, __name(_e2, "h"), _e2), X = (_f = class extends Error {
  constructor(r) {
    super(_(3));
  }
}, __name(_f, "X"), _f), V = (_g = class extends Error {
  constructor(r) {
    super(_(4));
  }
}, __name(_g, "V"), _g), Re = (_h = class extends Error {
  constructor(t) {
    super(_(5));
    this.value = t;
  }
}, __name(_h, "Re"), _h), Pe = (_i = class extends Error {
  constructor(r) {
    super(_(6));
  }
}, __name(_i, "Pe"), _i), Je = (_j = class extends Error {
  constructor(r) {
    super(_(7));
  }
}, __name(_j, "Je"), _j), O = (_k = class extends Error {
  constructor(r) {
    super(_(8));
  }
}, __name(_k, "O"), _k), Q = (_l = class extends Error {
  constructor(r) {
    super(_(9));
  }
}, __name(_l, "Q"), _l);
var j = (_m = class {
  constructor(r, t) {
    this.value = r;
    this.replacement = t;
  }
}, __name(_m, "j"), _m);
var ee = /* @__PURE__ */ __name(() => {
  let e = { p: 0, s: 0, f: 0 };
  return e.p = new Promise((r, t) => {
    e.s = r, e.f = t;
  }), e;
}, "ee"), An = /* @__PURE__ */ __name((e, r) => {
  e.s(r), e.p.s = 1, e.p.v = r;
}, "An"), En = /* @__PURE__ */ __name((e, r) => {
  e.f(r), e.p.s = 2, e.p.v = r;
}, "En"), Nt = ee.toString(), bt = An.toString(), vt = En.toString(), Pr = /* @__PURE__ */ __name(() => {
  let e = [], r = [], t = true, n = false, a = 0, s = /* @__PURE__ */ __name((l, g, S) => {
    for (S = 0; S < a; S++) r[S] && r[S][g](l);
  }, "s"), i = /* @__PURE__ */ __name((l, g, S, d) => {
    for (g = 0, S = e.length; g < S; g++) d = e[g], !t && g === S - 1 ? l[n ? "return" : "throw"](d) : l.next(d);
  }, "i"), u = /* @__PURE__ */ __name((l, g) => (t && (g = a++, r[g] = l), i(l), () => {
    t && (r[g] = r[a], r[a--] = void 0);
  }), "u");
  return { __SEROVAL_STREAM__: true, on: /* @__PURE__ */ __name((l) => u(l), "on"), next: /* @__PURE__ */ __name((l) => {
    t && (e.push(l), s(l, "next"));
  }, "next"), throw: /* @__PURE__ */ __name((l) => {
    t && (e.push(l), s(l, "throw"), t = false, n = false, r.length = 0);
  }, "throw"), return: /* @__PURE__ */ __name((l) => {
    t && (e.push(l), s(l, "return"), t = false, n = true, r.length = 0);
  }, "return") };
}, "Pr"), Ct = Pr.toString(), xr = /* @__PURE__ */ __name((e) => (r) => () => {
  let t = 0, n = { [e]: () => n, next: /* @__PURE__ */ __name(() => {
    if (t > r.d) return { done: true, value: void 0 };
    let a = t++, s = r.v[a];
    if (a === r.t) throw s;
    return { done: a === r.d, value: s };
  }, "next") };
  return n;
}, "xr"), At = xr.toString(), Tr = /* @__PURE__ */ __name((e, r) => (t) => () => {
  let n = 0, a = -1, s = false, i = [], u = [], l = /* @__PURE__ */ __name((S = 0, d = u.length) => {
    for (; S < d; S++) u[S].s({ done: true, value: void 0 });
  }, "l");
  t.on({ next: /* @__PURE__ */ __name((S) => {
    let d = u.shift();
    d && d.s({ done: false, value: S }), i.push(S);
  }, "next"), throw: /* @__PURE__ */ __name((S) => {
    let d = u.shift();
    d && d.f(S), l(), a = i.length, s = true, i.push(S);
  }, "throw"), return: /* @__PURE__ */ __name((S) => {
    let d = u.shift();
    d && d.s({ done: true, value: S }), l(), a = i.length, i.push(S);
  }, "return") });
  let g = { [e]: () => g, next: /* @__PURE__ */ __name(() => {
    if (a === -1) {
      let G = n++;
      if (G >= i.length) {
        let rt = r();
        return u.push(rt), rt.p;
      }
      return { done: false, value: i[G] };
    }
    if (n > a) return { done: true, value: void 0 };
    let S = n++, d = i[S];
    if (S !== a) return { done: false, value: d };
    if (s) throw d;
    return { done: true, value: d };
  }, "next") };
  return g;
}, "Tr"), Et = Tr.toString(), Or = /* @__PURE__ */ __name((e) => {
  let r = atob(e), t = r.length, n = new Uint8Array(t);
  for (let a = 0; a < t; a++) n[a] = r.charCodeAt(a);
  return n.buffer;
}, "Or"), It = Or.toString();
function Ze(e) {
  return "__SEROVAL_SEQUENCE__" in e;
}
__name(Ze, "Ze");
function wr(e, r, t) {
  return { __SEROVAL_SEQUENCE__: true, v: e, t: r, d: t };
}
__name(wr, "wr");
function $e(e) {
  let r = [], t = -1, n = -1, a = e[C]();
  for (; ; ) try {
    let s = a.next();
    if (r.push(s.value), s.done) {
      n = r.length - 1;
      break;
    }
  } catch (s) {
    t = r.length, r.push(s);
  }
  return wr(r, t, n);
}
__name($e, "$e");
var In = xr(C);
function Rt(e) {
  return In(e);
}
__name(Rt, "Rt");
var Pt = {}, xt = {};
var Tt = { 0: {}, 1: {}, 2: {}, 3: {}, 4: {}, 5: {} }, Ot = { 0: "[]", 1: Nt, 2: bt, 3: vt, 4: Ct, 5: It };
function Xe(e) {
  return "__SEROVAL_STREAM__" in e;
}
__name(Xe, "Xe");
function re() {
  return Pr();
}
__name(re, "re");
function Qe(e) {
  let r = re(), t = e[v]();
  async function n() {
    try {
      let a = await t.next();
      a.done ? r.return(a.value) : (r.next(a.value), await n());
    } catch (a) {
      r.throw(a);
    }
  }
  __name(n, "n");
  return n().catch(() => {
  }), r;
}
__name(Qe, "Qe");
var Rn = Tr(v, ee);
function wt(e) {
  return Rn(e);
}
__name(wt, "wt");
async function hr(e) {
  try {
    return [1, await e];
  } catch (r) {
    return [0, r];
  }
}
__name(hr, "hr");
function me(e, r) {
  return { plugins: r.plugins, mode: e, marked: /* @__PURE__ */ new Set(), features: 63 ^ (r.disabledFeatures || 0), refs: r.refs || /* @__PURE__ */ new Map(), depthLimit: r.depthLimit || 1e3 };
}
__name(me, "me");
function pe(e, r) {
  e.marked.add(r);
}
__name(pe, "pe");
function zr(e, r) {
  let t = e.refs.size;
  return e.refs.set(r, t), t;
}
__name(zr, "zr");
function er(e, r) {
  let t = e.refs.get(r);
  return t != null ? (pe(e, t), { type: 1, value: pt(t) }) : { type: 0, value: zr(e, r) };
}
__name(er, "er");
function Y(e, r) {
  let t = er(e, r);
  return t.type === 1 ? t : Ir(r) ? { type: 2, value: gt(t.value, r) } : t;
}
__name(Y, "Y");
function I(e, r) {
  let t = Y(e, r);
  if (t.type !== 0) return t.value;
  if (r in ve) return dt(t.value, r);
  throw new x(r);
}
__name(I, "I");
function k(e, r) {
  let t = er(e, Tt[r]);
  return t.type === 1 ? t.value : c(26, t.value, r, o, o, o, o, o, o, o, o, o);
}
__name(k, "k");
function rr(e) {
  let r = er(e, Pt);
  return r.type === 1 ? r.value : c(27, r.value, o, o, o, o, o, o, I(e, C), o, o, o);
}
__name(rr, "rr");
function tr(e) {
  let r = er(e, xt);
  return r.type === 1 ? r.value : c(29, r.value, o, o, o, o, o, [k(e, 1), I(e, v)], o, o, o, o);
}
__name(tr, "tr");
function nr(e, r, t, n) {
  return c(t ? 11 : 10, e, o, o, o, n, o, o, o, o, Te(r), o);
}
__name(nr, "nr");
function or(e, r, t, n) {
  return c(8, r, o, o, o, o, { k: t, v: n }, o, k(e, 0), o, o, o);
}
__name(or, "or");
function zt(e, r, t) {
  return c(22, r, t, o, o, o, o, o, k(e, 1), o, o, o);
}
__name(zt, "zt");
function ar(e, r, t) {
  let n = new Uint8Array(t), a = "";
  for (let s = 0, i = n.length; s < i; s++) a += String.fromCharCode(n[s]);
  return c(19, r, y(btoa(a)), o, o, o, o, o, k(e, 5), o, o, o);
}
__name(ar, "ar");
function te(e, r) {
  return { base: me(e, r), child: void 0 };
}
__name(te, "te");
var kr = (_n2 = class {
  constructor(r, t) {
    this._p = r;
    this.depth = t;
  }
  parse(r) {
    return N(this._p, this.depth, r);
  }
}, __name(_n2, "kr"), _n2);
async function xn(e, r, t) {
  let n = [];
  for (let a = 0, s = t.length; a < s; a++) a in t ? n[a] = await N(e, r, t[a]) : n[a] = 0;
  return n;
}
__name(xn, "xn");
async function Tn(e, r, t, n) {
  return _e(t, n, await xn(e, r, n));
}
__name(Tn, "Tn");
async function Dr(e, r, t) {
  let n = Object.entries(t), a = [], s = [];
  for (let i = 0, u = n.length; i < u; i++) a.push(y(n[i][0])), s.push(await N(e, r, n[i][1]));
  return C in t && (a.push(I(e.base, C)), s.push(Ue(rr(e.base), await N(e, r, $e(t))))), v in t && (a.push(I(e.base, v)), s.push(je(tr(e.base), await N(e, r, Qe(t))))), P in t && (a.push(I(e.base, P)), s.push($(t[P]))), R in t && (a.push(I(e.base, R)), s.push(t[R] ? H : J)), { k: a, v: s };
}
__name(Dr, "Dr");
async function _r(e, r, t, n, a) {
  return nr(t, n, a, await Dr(e, r, n));
}
__name(_r, "_r");
async function On(e, r, t, n) {
  return ke(t, await N(e, r, n.valueOf()));
}
__name(On, "On");
async function wn(e, r, t, n) {
  return De(t, n, await N(e, r, n.buffer));
}
__name(wn, "wn");
async function hn(e, r, t, n) {
  return Fe(t, n, await N(e, r, n.buffer));
}
__name(hn, "hn");
async function zn(e, r, t, n) {
  return Be(t, n, await N(e, r, n.buffer));
}
__name(zn, "zn");
async function _t(e, r, t, n) {
  let a = Z(n, e.base.features);
  return Ve(t, n, a ? await Dr(e, r, a) : o);
}
__name(_t, "_t");
async function _n(e, r, t, n) {
  let a = Z(n, e.base.features);
  return Me(t, n, a ? await Dr(e, r, a) : o);
}
__name(_n, "_n");
async function kn(e, r, t, n) {
  let a = [], s = [];
  for (let [i, u] of n.entries()) a.push(await N(e, r, i)), s.push(await N(e, r, u));
  return or(e.base, t, a, s);
}
__name(kn, "kn");
async function Dn(e, r, t, n) {
  let a = [];
  for (let s of n.keys()) a.push(await N(e, r, s));
  return Le(t, a);
}
__name(Dn, "Dn");
async function kt(e, r, t, n) {
  let a = e.base.plugins;
  if (a) for (let s = 0, i = a.length; s < i; s++) {
    let u = a[s];
    if (u.parse.async && u.test(n)) return ce(t, u.tag, await u.parse.async(n, new kr(e, r), { id: t }));
  }
  return o;
}
__name(kt, "kt");
async function Fn(e, r, t, n) {
  let [a, s] = await hr(n);
  return c(12, t, a, o, o, o, o, o, await N(e, r, s), o, o, o);
}
__name(Fn, "Fn");
function Bn(e, r, t, n, a) {
  let s = [], i = t.on({ next: /* @__PURE__ */ __name((u) => {
    pe(this.base, r), N(this, e, u).then((l) => {
      s.push(qe(r, l));
    }, (l) => {
      a(l), i();
    });
  }, "next"), throw: /* @__PURE__ */ __name((u) => {
    pe(this.base, r), N(this, e, u).then((l) => {
      s.push(We(r, l)), n(s), i();
    }, (l) => {
      a(l), i();
    });
  }, "throw"), return: /* @__PURE__ */ __name((u) => {
    pe(this.base, r), N(this, e, u).then((l) => {
      s.push(Ge(r, l)), n(s), i();
    }, (l) => {
      a(l), i();
    });
  }, "return") });
}
__name(Bn, "Bn");
async function Vn(e, r, t, n) {
  return Ye(t, k(e.base, 4), await new Promise(Bn.bind(e, r, t, n)));
}
__name(Vn, "Vn");
async function Mn(e, r, t, n) {
  let a = [];
  for (let s = 0, i = n.v.length; s < i; s++) a[s] = await N(e, r, n.v[s]);
  return Ke(t, a, n.t, n.d);
}
__name(Mn, "Mn");
async function Ln(e, r, t, n) {
  if (Array.isArray(n)) return Tn(e, r, t, n);
  if (Xe(n)) return Vn(e, r, t, n);
  if (Ze(n)) return Mn(e, r, t, n);
  let a = n.constructor;
  if (a === j) return N(e, r, n.replacement);
  let s = await kt(e, r, t, n);
  if (s) return s;
  switch (a) {
    case Object:
      return _r(e, r, t, n, false);
    case o:
      return _r(e, r, t, n, true);
    case Date:
      return he(t, n);
    case Error:
    case EvalError:
    case RangeError:
    case ReferenceError:
    case SyntaxError:
    case TypeError:
    case URIError:
      return _t(e, r, t, n);
    case Number:
    case Boolean:
    case String:
    case BigInt:
      return On(e, r, t, n);
    case ArrayBuffer:
      return ar(e.base, t, n);
    case Int8Array:
    case Int16Array:
    case Int32Array:
    case Uint8Array:
    case Uint16Array:
    case Uint32Array:
    case Uint8ClampedArray:
    case Float32Array:
    case Float64Array:
      return wn(e, r, t, n);
    case DataView:
      return zn(e, r, t, n);
    case Map:
      return kn(e, r, t, n);
    case Set:
      return Dn(e, r, t, n);
  }
  if (a === Promise || n instanceof Promise) return Fn(e, r, t, n);
  let i = e.base.features;
  if (i & 32 && a === RegExp) return ze(t, n);
  if (i & 16) switch (a) {
    case BigInt64Array:
    case BigUint64Array:
      return hn(e, r, t, n);
  }
  if (i & 1 && typeof AggregateError != "undefined" && (a === AggregateError || n instanceof AggregateError)) return _n(e, r, t, n);
  if (n instanceof Error) return _t(e, r, t, n);
  if (C in n || v in n) return _r(e, r, t, n, !!a);
  throw new x(n);
}
__name(Ln, "Ln");
async function Un(e, r, t) {
  let n = Y(e.base, t);
  if (n.type !== 0) return n.value;
  let a = await kt(e, r, n.value, t);
  if (a) return a;
  throw new x(t);
}
__name(Un, "Un");
async function N(e, r, t) {
  switch (typeof t) {
    case "boolean":
      return t ? H : J;
    case "undefined":
      return Ae;
    case "string":
      return $(t);
    case "number":
      return Oe(t);
    case "bigint":
      return we(t);
    case "object": {
      if (t) {
        let n = Y(e.base, t);
        return n.type === 0 ? await Ln(e, r + 1, n.value, t) : n.value;
      }
      return Ee;
    }
    case "symbol":
      return I(e.base, t);
    case "function":
      return Un(e, r, t);
    default:
      throw new x(t);
  }
}
__name(N, "N");
async function ne(e, r) {
  try {
    return await N(e, 0, r);
  } catch (t) {
    throw t instanceof z ? t : new z(t);
  }
}
__name(ne, "ne");
var oe = ((t) => (t[t.Vanilla = 1] = "Vanilla", t[t.Cross = 2] = "Cross", t))(oe || {});
function ai(e) {
  return e;
}
__name(ai, "ai");
function Dt(e, r) {
  for (let t = 0, n = r.length; t < n; t++) {
    let a = r[t];
    e.has(a) || (e.add(a), a.extends && Dt(e, a.extends));
  }
}
__name(Dt, "Dt");
function A(e) {
  if (e) {
    let r = /* @__PURE__ */ new Set();
    return Dt(r, e), [...r];
  }
}
__name(A, "A");
function Ft(e) {
  switch (e) {
    case "Int8Array":
      return Int8Array;
    case "Int16Array":
      return Int16Array;
    case "Int32Array":
      return Int32Array;
    case "Uint8Array":
      return Uint8Array;
    case "Uint16Array":
      return Uint16Array;
    case "Uint32Array":
      return Uint32Array;
    case "Uint8ClampedArray":
      return Uint8ClampedArray;
    case "Float32Array":
      return Float32Array;
    case "Float64Array":
      return Float64Array;
    case "BigInt64Array":
      return BigInt64Array;
    case "BigUint64Array":
      return BigUint64Array;
    default:
      throw new Je(e);
  }
}
__name(Ft, "Ft");
var jn = 1e6, Yn = 1e4, qn = 2e4;
function Vt(e, r) {
  switch (r) {
    case 3:
      return Object.freeze(e);
    case 1:
      return Object.preventExtensions(e);
    case 2:
      return Object.seal(e);
    default:
      return e;
  }
}
__name(Vt, "Vt");
var Wn = 1e3;
function Mt(e, r) {
  var n;
  let t = r.refs || /* @__PURE__ */ new Map();
  return "types" in t || Object.assign(t, { types: /* @__PURE__ */ new Map() }), { mode: e, plugins: r.plugins, refs: t, features: (n = r.features) != null ? n : 63 ^ (r.disabledFeatures || 0), depthLimit: r.depthLimit || Wn };
}
__name(Mt, "Mt");
function Lt(e) {
  return { mode: 1, base: Mt(1, e), child: o, state: { marked: new Set(e.markedRefs) } };
}
__name(Lt, "Lt");
var Fr = (_o2 = class {
  constructor(r, t) {
    this._p = r;
    this.depth = t;
  }
  deserialize(r) {
    return p(this._p, this.depth, r);
  }
}, __name(_o2, "Fr"), _o2);
function jt(e, r) {
  if (r < 0 || !Number.isFinite(r) || !Number.isInteger(r)) throw new O({ t: 4, i: r });
  if (e.refs.has(r)) throw new Error("Conflicted ref id: " + r);
}
__name(jt, "jt");
function Gn(e, r, t) {
  return jt(e.base, r), e.state.marked.has(r) && e.base.refs.set(r, t), t;
}
__name(Gn, "Gn");
function Kn(e, r, t) {
  return jt(e.base, r), e.base.refs.set(r, t), t;
}
__name(Kn, "Kn");
function b(e, r, t) {
  return e.mode === 1 ? Gn(e, r, t) : Kn(e, r, t);
}
__name(b, "b");
function Br(e, r, t) {
  if (Object.hasOwn(r, t)) return r[t];
  throw new O(e);
}
__name(Br, "Br");
function Hn(e, r) {
  return b(e, r.i, St(D(r.s)));
}
__name(Hn, "Hn");
function Jn(e, r, t) {
  let n = t.a, a = n.length, s = b(e, t.i, new Array(a));
  for (let i = 0, u; i < a; i++) u = n[i], u && (s[i] = p(e, r, u));
  return Vt(s, t.o), s;
}
__name(Jn, "Jn");
function Zn(e) {
  switch (e) {
    case "constructor":
    case "__proto__":
    case "prototype":
    case "__defineGetter__":
    case "__defineSetter__":
    case "__lookupGetter__":
    case "__lookupSetter__":
      return false;
    default:
      return true;
  }
}
__name(Zn, "Zn");
function $n(e) {
  switch (e) {
    case v:
    case R:
    case P:
    case C:
      return true;
    default:
      return false;
  }
}
__name($n, "$n");
function Bt(e, r, t) {
  Zn(r) ? e[r] = t : Object.defineProperty(e, r, { value: t, configurable: true, enumerable: true, writable: true });
}
__name(Bt, "Bt");
function Xn(e, r, t, n, a) {
  if (typeof n == "string") Bt(t, D(n), p(e, r, a));
  else {
    let s = p(e, r, n);
    switch (typeof s) {
      case "string":
        Bt(t, s, p(e, r, a));
        break;
      case "symbol":
        $n(s) && (t[s] = p(e, r, a));
        break;
      default:
        throw new O(n);
    }
  }
}
__name(Xn, "Xn");
function Yt(e, r, t) {
  e.base.refs.types.set(r, t);
}
__name(Yt, "Yt");
function de(e, r, t, n) {
  if (e.base.refs.types.get(t) !== n) throw new O(r);
}
__name(de, "de");
function qt(e, r, t, n) {
  let a = t.k;
  if (a.length > 0) for (let i = 0, u = t.v, l = a.length; i < l; i++) Xn(e, r, n, a[i], u[i]);
  return n;
}
__name(qt, "qt");
function Qn(e, r, t) {
  let n = b(e, t.i, t.t === 10 ? {} : /* @__PURE__ */ Object.create(null));
  return qt(e, r, t.p, n), Vt(n, t.o), n;
}
__name(Qn, "Qn");
function eo(e, r) {
  return b(e, r.i, new Date(r.s));
}
__name(eo, "eo");
function ro(e, r) {
  if (e.base.features & 32) {
    let t = D(r.c);
    if (t.length > qn) throw new O(r);
    return b(e, r.i, new RegExp(t, r.m));
  }
  throw new h(r);
}
__name(ro, "ro");
function to(e, r, t) {
  let n = b(e, t.i, /* @__PURE__ */ new Set());
  for (let a = 0, s = t.a, i = s.length; a < i; a++) n.add(p(e, r, s[a]));
  return n;
}
__name(to, "to");
function no(e, r, t) {
  let n = b(e, t.i, /* @__PURE__ */ new Map());
  for (let a = 0, s = t.e.k, i = t.e.v, u = s.length; a < u; a++) n.set(p(e, r, s[a]), p(e, r, i[a]));
  return n;
}
__name(no, "no");
function oo(e, r) {
  if (r.s.length > jn) throw new O(r);
  return b(e, r.i, Or(D(r.s)));
}
__name(oo, "oo");
function ao(e, r, t) {
  var u;
  let n = Ft(t.c), a = p(e, r, t.f), s = (u = t.b) != null ? u : 0;
  if (s < 0 || s > a.byteLength) throw new O(t);
  return b(e, t.i, new n(a, s, t.l));
}
__name(ao, "ao");
function so(e, r, t) {
  var i;
  let n = p(e, r, t.f), a = (i = t.b) != null ? i : 0;
  if (a < 0 || a > n.byteLength) throw new O(t);
  return b(e, t.i, new DataView(n, a, t.l));
}
__name(so, "so");
function Wt(e, r, t, n) {
  if (t.p) {
    let a = qt(e, r, t.p, {});
    Object.defineProperties(n, Object.getOwnPropertyDescriptors(a));
  }
  return n;
}
__name(Wt, "Wt");
function io(e, r, t) {
  let n = b(e, t.i, new AggregateError([], D(t.m)));
  return Wt(e, r, t, n);
}
__name(io, "io");
function uo(e, r, t) {
  let n = Br(t, st, t.s), a = b(e, t.i, new n(D(t.m)));
  return Wt(e, r, t, a);
}
__name(uo, "uo");
function lo(e, r, t) {
  let n = ee(), a = b(e, t.i, n.p), s = p(e, r, t.f);
  return t.s ? n.s(s) : n.f(s), a;
}
__name(lo, "lo");
function co(e, r, t) {
  return b(e, t.i, Object(p(e, r, t.f)));
}
__name(co, "co");
function fo(e, r, t) {
  let n = e.base.plugins;
  if (n) {
    let a = D(t.c);
    for (let s = 0, i = n.length; s < i; s++) {
      let u = n[s];
      if (u.tag === a) return b(e, t.i, u.deserialize(t.s, new Fr(e, r), { id: t.i }));
    }
  }
  throw new X(t.c);
}
__name(fo, "fo");
function So(e, r) {
  let t = b(e, r.i, b(e, r.s, ee()).p);
  return Yt(e, r.s, 22), t;
}
__name(So, "So");
function mo(e, r, t) {
  let n = e.base.refs.get(t.i);
  if (n) return de(e, t, t.i, 22), n.s(p(e, r, t.a[1])), o;
  throw new V("Promise");
}
__name(mo, "mo");
function po(e, r, t) {
  let n = e.base.refs.get(t.i);
  if (n) return de(e, t, t.i, 22), n.f(p(e, r, t.a[1])), o;
  throw new V("Promise");
}
__name(po, "po");
function go(e, r, t) {
  p(e, r, t.a[0]);
  let n = p(e, r, t.a[1]);
  return Rt(n);
}
__name(go, "go");
function yo(e, r, t) {
  p(e, r, t.a[0]);
  let n = p(e, r, t.a[1]);
  return wt(n);
}
__name(yo, "yo");
function No(e, r, t) {
  let n = b(e, t.i, re());
  Yt(e, t.i, 31);
  let a = t.a, s = a.length;
  if (s) for (let i = 0; i < s; i++) p(e, r, a[i]);
  return n;
}
__name(No, "No");
function bo(e, r, t) {
  let n = e.base.refs.get(t.i);
  if (n) return de(e, t, t.i, 31), n.next(p(e, r, t.f)), o;
  throw new V("Stream");
}
__name(bo, "bo");
function vo(e, r, t) {
  let n = e.base.refs.get(t.i);
  if (n) return de(e, t, t.i, 31), n.throw(p(e, r, t.f)), o;
  throw new V("Stream");
}
__name(vo, "vo");
function Co(e, r, t) {
  let n = e.base.refs.get(t.i);
  if (n) return de(e, t, t.i, 31), n.return(p(e, r, t.f)), o;
  throw new V("Stream");
}
__name(Co, "Co");
function Ao(e, r, t) {
  return p(e, r, t.f), o;
}
__name(Ao, "Ao");
function Eo(e, r, t) {
  return p(e, r, t.a[1]), o;
}
__name(Eo, "Eo");
function Io(e, r, t) {
  let n = b(e, t.i, wr([], t.s, t.l));
  for (let a = 0, s = t.a.length; a < s; a++) n.v[a] = p(e, r, t.a[a]);
  return n;
}
__name(Io, "Io");
function p(e, r, t) {
  if (r > e.base.depthLimit) throw new Q(e.base.depthLimit);
  switch (r += 1, t.t) {
    case 2:
      return Br(t, at, t.s);
    case 0:
      return Number(t.s);
    case 1:
      return D(String(t.s));
    case 3:
      if (String(t.s).length > Yn) throw new O(t);
      return BigInt(t.s);
    case 4:
      return e.base.refs.get(t.i);
    case 18:
      return Hn(e, t);
    case 9:
      return Jn(e, r, t);
    case 10:
    case 11:
      return Qn(e, r, t);
    case 5:
      return eo(e, t);
    case 6:
      return ro(e, t);
    case 7:
      return to(e, r, t);
    case 8:
      return no(e, r, t);
    case 19:
      return oo(e, t);
    case 16:
    case 15:
      return ao(e, r, t);
    case 20:
      return so(e, r, t);
    case 14:
      return io(e, r, t);
    case 13:
      return uo(e, r, t);
    case 12:
      return lo(e, r, t);
    case 17:
      return Br(t, nt, t.s);
    case 21:
      return co(e, r, t);
    case 25:
      return fo(e, r, t);
    case 22:
      return So(e, t);
    case 23:
      return mo(e, r, t);
    case 24:
      return po(e, r, t);
    case 28:
      return go(e, r, t);
    case 30:
      return yo(e, r, t);
    case 31:
      return No(e, r, t);
    case 32:
      return bo(e, r, t);
    case 33:
      return vo(e, r, t);
    case 34:
      return Co(e, r, t);
    case 27:
      return Ao(e, r, t);
    case 29:
      return Eo(e, r, t);
    case 35:
      return Io(e, r, t);
    default:
      throw new h(t);
  }
}
__name(p, "p");
function sr(e, r) {
  try {
    return p(e, 0, r);
  } catch (t) {
    throw new He(t);
  }
}
__name(sr, "sr");
var Ro = /* @__PURE__ */ __name(() => T, "Ro"), Po = Ro.toString(), Gt = /=>/.test(Po);
function ir(e, r) {
  return Gt ? (e.length === 1 ? e[0] : "(" + e.join(",") + ")") + "=>" + (r.startsWith("{") ? "(" + r + ")" : r) : "function(" + e.join(",") + "){return " + r + "}";
}
__name(ir, "ir");
function Kt(e, r) {
  return Gt ? (e.length === 1 ? e[0] : "(" + e.join(",") + ")") + "=>{" + r + "}" : "function(" + e.join(",") + "){" + r + "}";
}
__name(Kt, "Kt");
var Zt = "hjkmoquxzABCDEFGHIJKLNPQRTUVWXYZ$_", Ht = Zt.length, $t = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$_", Jt = $t.length;
function Vr(e) {
  let r = e % Ht, t = Zt[r];
  for (e = (e - r) / Ht; e > 0; ) r = e % Jt, t += $t[r], e = (e - r) / Jt;
  return t;
}
__name(Vr, "Vr");
var xo = /^[$A-Z_][0-9A-Z_$]*$/i;
function Mr(e) {
  let r = e[0];
  return (r === "$" || r === "_" || r >= "A" && r <= "Z" || r >= "a" && r <= "z") && xo.test(e);
}
__name(Mr, "Mr");
function ye(e) {
  switch (e.t) {
    case 0:
      return e.s + "=" + e.v;
    case 2:
      return e.s + ".set(" + e.k + "," + e.v + ")";
    case 1:
      return e.s + ".add(" + e.v + ")";
    case 3:
      return e.s + ".delete(" + e.k + ")";
  }
}
__name(ye, "ye");
function To(e) {
  let r = [], t = e[0];
  for (let n = 1, a = e.length, s, i = t; n < a; n++) s = e[n], s.t === 0 && s.v === i.v ? t = { t: 0, s: s.s, k: o, v: ye(t) } : s.t === 2 && s.s === i.s ? t = { t: 2, s: ye(t), k: s.k, v: s.v } : s.t === 1 && s.s === i.s ? t = { t: 1, s: ye(t), k: o, v: s.v } : s.t === 3 && s.s === i.s ? t = { t: 3, s: ye(t), k: s.k, v: o } : (r.push(t), t = s), i = s;
  return r.push(t), r;
}
__name(To, "To");
function on(e) {
  if (e.length) {
    let r = "", t = To(e);
    for (let n = 0, a = t.length; n < a; n++) r += ye(t[n]) + ",";
    return r;
  }
  return o;
}
__name(on, "on");
var Oo = "Object.create(null)", wo = "new Set", ho = "new Map", zo = "Promise.resolve", _o = "Promise.reject", ko = { 3: "Object.freeze", 2: "Object.seal", 1: "Object.preventExtensions", 0: o };
function an(e, r) {
  return { mode: e, plugins: r.plugins, features: r.features, marked: new Set(r.markedRefs), stack: [], flags: [], assignments: [] };
}
__name(an, "an");
function lr(e) {
  return { mode: 2, base: an(2, e), state: e, child: o };
}
__name(lr, "lr");
var Lr = (_p = class {
  constructor(r) {
    this._p = r;
  }
  serialize(r) {
    return f(this._p, r);
  }
}, __name(_p, "Lr"), _p);
function Fo(e, r) {
  let t = e.valid.get(r);
  t == null && (t = e.valid.size, e.valid.set(r, t));
  let n = e.vars[t];
  return n == null && (n = Vr(t), e.vars[t] = n), n;
}
__name(Fo, "Fo");
function Bo(e) {
  return le + "[" + e + "]";
}
__name(Bo, "Bo");
function m(e, r) {
  return e.mode === 1 ? Fo(e.state, r) : Bo(r);
}
__name(m, "m");
function w(e, r) {
  e.marked.add(r);
}
__name(w, "w");
function Ur(e, r) {
  return e.marked.has(r);
}
__name(Ur, "Ur");
function Yr(e, r, t) {
  r !== 0 && (w(e.base, t), e.base.flags.push({ type: r, value: m(e, t) }));
}
__name(Yr, "Yr");
function Vo(e) {
  let r = "";
  for (let t = 0, n = e.flags, a = n.length; t < a; t++) {
    let s = n[t];
    r += ko[s.type] + "(" + s.value + "),";
  }
  return r;
}
__name(Vo, "Vo");
function sn(e) {
  let r = on(e.assignments), t = Vo(e);
  return r ? t ? r + t : r : t;
}
__name(sn, "sn");
function qr(e, r, t) {
  e.assignments.push({ t: 0, s: r, k: o, v: t });
}
__name(qr, "qr");
function Mo(e, r, t) {
  e.base.assignments.push({ t: 1, s: m(e, r), k: o, v: t });
}
__name(Mo, "Mo");
function ge(e, r, t, n) {
  e.base.assignments.push({ t: 2, s: m(e, r), k: t, v: n });
}
__name(ge, "ge");
function Xt(e, r, t) {
  e.base.assignments.push({ t: 3, s: m(e, r), k: t, v: o });
}
__name(Xt, "Xt");
function Ne(e, r, t, n) {
  qr(e.base, m(e, r) + "[" + t + "]", n);
}
__name(Ne, "Ne");
function jr(e, r, t, n) {
  qr(e.base, m(e, r) + "." + t, n);
}
__name(jr, "jr");
function Lo(e, r, t, n) {
  qr(e.base, m(e, r) + ".v[" + t + "]", n);
}
__name(Lo, "Lo");
function F(e, r) {
  return r.t === 4 && e.stack.includes(r.i);
}
__name(F, "F");
function ae(e, r, t) {
  return e.mode === 1 && !Ur(e.base, r) ? t : m(e, r) + "=" + t;
}
__name(ae, "ae");
function Uo(e) {
  return L + '.get("' + e.s + '")';
}
__name(Uo, "Uo");
function Qt(e, r, t, n) {
  return t ? F(e.base, t) ? (w(e.base, r), Ne(e, r, n, m(e, t.i)), "") : f(e, t) : "";
}
__name(Qt, "Qt");
function jo(e, r) {
  let t = r.i, n = r.a, a = n.length;
  if (a > 0) {
    e.base.stack.push(t);
    let s = Qt(e, t, n[0], 0), i = s === "";
    for (let u = 1, l; u < a; u++) l = Qt(e, t, n[u], u), s += "," + l, i = l === "";
    return e.base.stack.pop(), Yr(e, r.o, r.i), "[" + s + (i ? ",]" : "]");
  }
  return "[]";
}
__name(jo, "jo");
function en(e, r, t, n) {
  if (typeof t == "string") {
    let a = Number(t), s = a >= 0 && a.toString() === t || Mr(t);
    if (F(e.base, n)) {
      let i = m(e, n.i);
      return w(e.base, r.i), s && a !== a ? jr(e, r.i, t, i) : Ne(e, r.i, s ? t : '"' + t + '"', i), "";
    }
    return (s ? t : '"' + t + '"') + ":" + f(e, n);
  }
  return "[" + f(e, t) + "]:" + f(e, n);
}
__name(en, "en");
function un(e, r, t) {
  let n = t.k, a = n.length;
  if (a > 0) {
    let s = t.v;
    e.base.stack.push(r.i);
    let i = en(e, r, n[0], s[0]);
    for (let u = 1, l = i; u < a; u++) l = en(e, r, n[u], s[u]), i += (l && i && ",") + l;
    return e.base.stack.pop(), "{" + i + "}";
  }
  return "{}";
}
__name(un, "un");
function Yo(e, r) {
  return Yr(e, r.o, r.i), un(e, r, r.p);
}
__name(Yo, "Yo");
function qo(e, r, t, n) {
  let a = un(e, r, t);
  return a !== "{}" ? "Object.assign(" + n + "," + a + ")" : n;
}
__name(qo, "qo");
function Wo(e, r, t, n, a) {
  let s = e.base, i = f(e, a), u = Number(n), l = u >= 0 && u.toString() === n || Mr(n);
  if (F(s, a)) l && u !== u ? jr(e, r.i, n, i) : Ne(e, r.i, l ? n : '"' + n + '"', i);
  else {
    let g = s.assignments;
    s.assignments = t, l && u !== u ? jr(e, r.i, n, i) : Ne(e, r.i, l ? n : '"' + n + '"', i), s.assignments = g;
  }
}
__name(Wo, "Wo");
function Go(e, r, t, n, a) {
  if (typeof n == "string") Wo(e, r, t, n, a);
  else {
    let s = e.base, i = s.stack;
    s.stack = [];
    let u = f(e, a);
    s.stack = i;
    let l = s.assignments;
    s.assignments = t, Ne(e, r.i, f(e, n), u), s.assignments = l;
  }
}
__name(Go, "Go");
function Ko(e, r, t) {
  let n = t.k, a = n.length;
  if (a > 0) {
    let s = [], i = t.v;
    e.base.stack.push(r.i);
    for (let u = 0; u < a; u++) Go(e, r, s, n[u], i[u]);
    return e.base.stack.pop(), on(s);
  }
  return o;
}
__name(Ko, "Ko");
function Wr(e, r, t) {
  if (r.p) {
    let n = e.base;
    if (n.features & 8) t = qo(e, r, r.p, t);
    else {
      w(n, r.i);
      let a = Ko(e, r, r.p);
      if (a) return "(" + ae(e, r.i, t) + "," + a + m(e, r.i) + ")";
    }
  }
  return t;
}
__name(Wr, "Wr");
function Ho(e, r) {
  return Yr(e, r.o, r.i), Wr(e, r, Oo);
}
__name(Ho, "Ho");
function Jo(e) {
  return 'new Date("' + e.s + '")';
}
__name(Jo, "Jo");
function Zo(e, r) {
  if (e.base.features & 32) return "/" + r.c + "/" + r.m;
  throw new h(r);
}
__name(Zo, "Zo");
function rn(e, r, t) {
  let n = e.base;
  return F(n, t) ? (w(n, r), Mo(e, r, m(e, t.i)), "") : f(e, t);
}
__name(rn, "rn");
function $o(e, r) {
  let t = wo, n = r.a, a = n.length, s = r.i;
  if (a > 0) {
    e.base.stack.push(s);
    let i = rn(e, s, n[0]);
    for (let u = 1, l = i; u < a; u++) l = rn(e, s, n[u]), i += (l && i && ",") + l;
    e.base.stack.pop(), i && (t += "([" + i + "])");
  }
  return t;
}
__name($o, "$o");
function tn(e, r, t, n, a) {
  let s = e.base;
  if (F(s, t)) {
    let i = m(e, t.i);
    if (w(s, r), F(s, n)) {
      let l = m(e, n.i);
      return ge(e, r, i, l), "";
    }
    if (n.t !== 4 && n.i != null && Ur(s, n.i)) {
      let l = "(" + f(e, n) + ",[" + a + "," + a + "])";
      return ge(e, r, i, m(e, n.i)), Xt(e, r, a), l;
    }
    let u = s.stack;
    return s.stack = [], ge(e, r, i, f(e, n)), s.stack = u, "";
  }
  if (F(s, n)) {
    let i = m(e, n.i);
    if (w(s, r), t.t !== 4 && t.i != null && Ur(s, t.i)) {
      let l = "(" + f(e, t) + ",[" + a + "," + a + "])";
      return ge(e, r, m(e, t.i), i), Xt(e, r, a), l;
    }
    let u = s.stack;
    return s.stack = [], ge(e, r, f(e, t), i), s.stack = u, "";
  }
  return "[" + f(e, t) + "," + f(e, n) + "]";
}
__name(tn, "tn");
function Xo(e, r) {
  let t = ho, n = r.e.k, a = n.length, s = r.i, i = r.f, u = m(e, i.i), l = e.base;
  if (a > 0) {
    let g = r.e.v;
    l.stack.push(s);
    let S = tn(e, s, n[0], g[0], u);
    for (let d = 1, G = S; d < a; d++) G = tn(e, s, n[d], g[d], u), S += (G && S && ",") + G;
    l.stack.pop(), S && (t += "([" + S + "])");
  }
  return i.t === 26 && (w(l, i.i), t = "(" + f(e, i) + "," + t + ")"), t;
}
__name(Xo, "Xo");
function Qo(e, r) {
  return q(e, r.f) + '("' + r.s + '")';
}
__name(Qo, "Qo");
function ea(e, r) {
  return "new " + r.c + "(" + f(e, r.f) + "," + r.b + "," + r.l + ")";
}
__name(ea, "ea");
function ra(e, r) {
  return "new DataView(" + f(e, r.f) + "," + r.b + "," + r.l + ")";
}
__name(ra, "ra");
function ta(e, r) {
  let t = r.i;
  e.base.stack.push(t);
  let n = Wr(e, r, 'new AggregateError([],"' + r.m + '")');
  return e.base.stack.pop(), n;
}
__name(ta, "ta");
function na(e, r) {
  return Wr(e, r, "new " + Ce[r.s] + '("' + r.m + '")');
}
__name(na, "na");
function oa(e, r) {
  let t, n = r.f, a = r.i, s = r.s ? zo : _o, i = e.base;
  if (F(i, n)) {
    let u = m(e, n.i);
    t = s + (r.s ? "().then(" + ir([], u) + ")" : "().catch(" + Kt([], "throw " + u) + ")");
  } else {
    i.stack.push(a);
    let u = f(e, n);
    i.stack.pop(), t = s + "(" + u + ")";
  }
  return t;
}
__name(oa, "oa");
function aa(e, r) {
  return "Object(" + f(e, r.f) + ")";
}
__name(aa, "aa");
function q(e, r) {
  let t = f(e, r);
  return r.t === 4 ? t : "(" + t + ")";
}
__name(q, "q");
function sa(e, r) {
  if (e.mode === 1) throw new h(r);
  return "(" + ae(e, r.s, q(e, r.f) + "()") + ").p";
}
__name(sa, "sa");
function ia(e, r) {
  if (e.mode === 1) throw new h(r);
  return q(e, r.a[0]) + "(" + m(e, r.i) + "," + f(e, r.a[1]) + ")";
}
__name(ia, "ia");
function ua(e, r) {
  if (e.mode === 1) throw new h(r);
  return q(e, r.a[0]) + "(" + m(e, r.i) + "," + f(e, r.a[1]) + ")";
}
__name(ua, "ua");
function la(e, r) {
  let t = e.base.plugins;
  if (t) for (let n = 0, a = t.length; n < a; n++) {
    let s = t[n];
    if (s.tag === r.c) return e.child == null && (e.child = new Lr(e)), s.serialize(r.s, e.child, { id: r.i });
  }
  throw new X(r.c);
}
__name(la, "la");
function ca(e, r) {
  let t = "", n = false;
  return r.f.t !== 4 && (w(e.base, r.f.i), t = "(" + f(e, r.f) + ",", n = true), t += ae(e, r.i, "(" + At + ")(" + m(e, r.f.i) + ")"), n && (t += ")"), t;
}
__name(ca, "ca");
function fa(e, r) {
  return q(e, r.a[0]) + "(" + f(e, r.a[1]) + ")";
}
__name(fa, "fa");
function Sa(e, r) {
  let t = r.a[0], n = r.a[1], a = e.base, s = "";
  t.t !== 4 && (w(a, t.i), s += "(" + f(e, t)), n.t !== 4 && (w(a, n.i), s += (s ? "," : "(") + f(e, n)), s && (s += ",");
  let i = ae(e, r.i, "(" + Et + ")(" + m(e, n.i) + "," + m(e, t.i) + ")");
  return s ? s + i + ")" : i;
}
__name(Sa, "Sa");
function ma(e, r) {
  return q(e, r.a[0]) + "(" + f(e, r.a[1]) + ")";
}
__name(ma, "ma");
function pa(e, r) {
  let t = ae(e, r.i, q(e, r.f) + "()"), n = r.a.length;
  if (n) {
    let a = f(e, r.a[0]);
    for (let s = 1; s < n; s++) a += "," + f(e, r.a[s]);
    return "(" + t + "," + a + "," + m(e, r.i) + ")";
  }
  return t;
}
__name(pa, "pa");
function da(e, r) {
  return m(e, r.i) + ".next(" + f(e, r.f) + ")";
}
__name(da, "da");
function ga(e, r) {
  return m(e, r.i) + ".throw(" + f(e, r.f) + ")";
}
__name(ga, "ga");
function ya(e, r) {
  return m(e, r.i) + ".return(" + f(e, r.f) + ")";
}
__name(ya, "ya");
function nn(e, r, t, n) {
  let a = e.base;
  return F(a, n) ? (w(a, r), Lo(e, r, t, m(e, n.i)), "") : f(e, n);
}
__name(nn, "nn");
function Na(e, r) {
  let t = r.a, n = t.length, a = r.i;
  if (n > 0) {
    e.base.stack.push(a);
    let s = nn(e, a, 0, t[0]);
    for (let i = 1, u = s; i < n; i++) u = nn(e, a, i, t[i]), s += (u && s && ",") + u;
    if (e.base.stack.pop(), s) return "{__SEROVAL_SEQUENCE__:!0,v:[" + s + "],t:" + r.s + ",d:" + r.l + "}";
  }
  return "{__SEROVAL_SEQUENCE__:!0,v:[],t:-1,d:0}";
}
__name(Na, "Na");
function ba(e, r) {
  switch (r.t) {
    case 17:
      return tt[r.s];
    case 18:
      return Uo(r);
    case 9:
      return jo(e, r);
    case 10:
      return Yo(e, r);
    case 11:
      return Ho(e, r);
    case 5:
      return Jo(r);
    case 6:
      return Zo(e, r);
    case 7:
      return $o(e, r);
    case 8:
      return Xo(e, r);
    case 19:
      return Qo(e, r);
    case 16:
    case 15:
      return ea(e, r);
    case 20:
      return ra(e, r);
    case 14:
      return ta(e, r);
    case 13:
      return na(e, r);
    case 12:
      return oa(e, r);
    case 21:
      return aa(e, r);
    case 22:
      return sa(e, r);
    case 25:
      return la(e, r);
    case 26:
      return Ot[r.s];
    case 35:
      return Na(e, r);
    default:
      throw new h(r);
  }
}
__name(ba, "ba");
function f(e, r) {
  switch (r.t) {
    case 2:
      return ot[r.s];
    case 0:
      return "" + r.s;
    case 1:
      return '"' + r.s + '"';
    case 3:
      return r.s + "n";
    case 4:
      return m(e, r.i);
    case 23:
      return ia(e, r);
    case 24:
      return ua(e, r);
    case 27:
      return ca(e, r);
    case 28:
      return fa(e, r);
    case 29:
      return Sa(e, r);
    case 30:
      return ma(e, r);
    case 31:
      return pa(e, r);
    case 32:
      return da(e, r);
    case 33:
      return ga(e, r);
    case 34:
      return ya(e, r);
    default:
      return ae(e, r.i, ba(e, r));
  }
}
__name(f, "f");
function fr(e, r) {
  let t = f(e, r), n = r.i;
  if (n == null) return t;
  let a = sn(e.base), s = m(e, n), i = e.state.scopeId, u = i == null ? "" : le, l = a ? "(" + t + "," + a + s + ")" : t;
  if (u === "") return r.t === 10 && !a ? "(" + l + ")" : l;
  let g = i == null ? "()" : "(" + le + '["' + y(i) + '"])';
  return "(" + ir([u], l) + ")" + g;
}
__name(fr, "fr");
var Kr = (_q = class {
  constructor(r, t) {
    this._p = r;
    this.depth = t;
  }
  parse(r) {
    return E(this._p, this.depth, r);
  }
}, __name(_q, "Kr"), _q), Hr = (_r2 = class {
  constructor(r, t) {
    this._p = r;
    this.depth = t;
  }
  parse(r) {
    return E(this._p, this.depth, r);
  }
  parseWithError(r) {
    return W(this._p, this.depth, r);
  }
  isAlive() {
    return this._p.state.alive;
  }
  pushPendingState() {
    Qr(this._p);
  }
  popPendingState() {
    be(this._p);
  }
  onParse(r) {
    se(this._p, r);
  }
  onError(r) {
    $r(this._p, r);
  }
}, __name(_r2, "Hr"), _r2);
function va(e) {
  return { alive: true, pending: 0, initial: true, buffer: [], onParse: e.onParse, onError: e.onError, onDone: e.onDone };
}
__name(va, "va");
function Jr(e) {
  return { type: 2, base: me(2, e), state: va(e) };
}
__name(Jr, "Jr");
function Ca(e, r, t) {
  let n = [];
  for (let a = 0, s = t.length; a < s; a++) a in t ? n[a] = E(e, r, t[a]) : n[a] = 0;
  return n;
}
__name(Ca, "Ca");
function Aa(e, r, t, n) {
  return _e(t, n, Ca(e, r, n));
}
__name(Aa, "Aa");
function Zr(e, r, t) {
  let n = Object.entries(t), a = [], s = [];
  for (let i = 0, u = n.length; i < u; i++) a.push(y(n[i][0])), s.push(E(e, r, n[i][1]));
  return C in t && (a.push(I(e.base, C)), s.push(Ue(rr(e.base), E(e, r, $e(t))))), v in t && (a.push(I(e.base, v)), s.push(je(tr(e.base), E(e, r, e.type === 1 ? re() : Qe(t))))), P in t && (a.push(I(e.base, P)), s.push($(t[P]))), R in t && (a.push(I(e.base, R)), s.push(t[R] ? H : J)), { k: a, v: s };
}
__name(Zr, "Zr");
function Gr(e, r, t, n, a) {
  return nr(t, n, a, Zr(e, r, n));
}
__name(Gr, "Gr");
function Ea(e, r, t, n) {
  return ke(t, E(e, r, n.valueOf()));
}
__name(Ea, "Ea");
function Ia(e, r, t, n) {
  return De(t, n, E(e, r, n.buffer));
}
__name(Ia, "Ia");
function Ra(e, r, t, n) {
  return Fe(t, n, E(e, r, n.buffer));
}
__name(Ra, "Ra");
function Pa(e, r, t, n) {
  return Be(t, n, E(e, r, n.buffer));
}
__name(Pa, "Pa");
function ln(e, r, t, n) {
  let a = Z(n, e.base.features);
  return Ve(t, n, a ? Zr(e, r, a) : o);
}
__name(ln, "ln");
function xa(e, r, t, n) {
  let a = Z(n, e.base.features);
  return Me(t, n, a ? Zr(e, r, a) : o);
}
__name(xa, "xa");
function Ta(e, r, t, n) {
  let a = [], s = [];
  for (let [i, u] of n.entries()) a.push(E(e, r, i)), s.push(E(e, r, u));
  return or(e.base, t, a, s);
}
__name(Ta, "Ta");
function Oa(e, r, t, n) {
  let a = [];
  for (let s of n.keys()) a.push(E(e, r, s));
  return Le(t, a);
}
__name(Oa, "Oa");
function wa(e, r, t, n) {
  let a = Ye(t, k(e.base, 4), []);
  return e.type === 1 || (Qr(e), n.on({ next: /* @__PURE__ */ __name((s) => {
    if (e.state.alive) {
      let i = W(e, r, s);
      i && se(e, qe(t, i));
    }
  }, "next"), throw: /* @__PURE__ */ __name((s) => {
    if (e.state.alive) {
      let i = W(e, r, s);
      i && se(e, We(t, i));
    }
    be(e);
  }, "throw"), return: /* @__PURE__ */ __name((s) => {
    if (e.state.alive) {
      let i = W(e, r, s);
      i && se(e, Ge(t, i));
    }
    be(e);
  }, "return") })), a;
}
__name(wa, "wa");
function ha(e, r, t) {
  if (this.state.alive) {
    let n = W(this, r, t);
    n && se(this, c(23, e, o, o, o, o, o, [k(this.base, 2), n], o, o, o, o)), be(this);
  }
}
__name(ha, "ha");
function za(e, r, t) {
  if (this.state.alive) {
    let n = W(this, r, t);
    n && se(this, c(24, e, o, o, o, o, o, [k(this.base, 3), n], o, o, o, o));
  }
  be(this);
}
__name(za, "za");
function _a(e, r, t, n) {
  let a = zr(e.base, {});
  return e.type === 2 && (Qr(e), n.then(ha.bind(e, a, r), za.bind(e, a, r))), zt(e.base, t, a);
}
__name(_a, "_a");
function ka(e, r, t, n, a) {
  for (let s = 0, i = a.length; s < i; s++) {
    let u = a[s];
    if (u.parse.sync && u.test(n)) return ce(t, u.tag, u.parse.sync(n, new Kr(e, r), { id: t }));
  }
  return o;
}
__name(ka, "ka");
function Da(e, r, t, n, a) {
  for (let s = 0, i = a.length; s < i; s++) {
    let u = a[s];
    if (u.parse.stream && u.test(n)) return ce(t, u.tag, u.parse.stream(n, new Hr(e, r), { id: t }));
  }
  return o;
}
__name(Da, "Da");
function cn(e, r, t, n) {
  let a = e.base.plugins;
  return a ? e.type === 1 ? ka(e, r, t, n, a) : Da(e, r, t, n, a) : o;
}
__name(cn, "cn");
function Fa(e, r, t, n) {
  let a = [];
  for (let s = 0, i = n.v.length; s < i; s++) a[s] = E(e, r, n.v[s]);
  return Ke(t, a, n.t, n.d);
}
__name(Fa, "Fa");
function Ba(e, r, t, n, a) {
  switch (a) {
    case Object:
      return Gr(e, r, t, n, false);
    case o:
      return Gr(e, r, t, n, true);
    case Date:
      return he(t, n);
    case Error:
    case EvalError:
    case RangeError:
    case ReferenceError:
    case SyntaxError:
    case TypeError:
    case URIError:
      return ln(e, r, t, n);
    case Number:
    case Boolean:
    case String:
    case BigInt:
      return Ea(e, r, t, n);
    case ArrayBuffer:
      return ar(e.base, t, n);
    case Int8Array:
    case Int16Array:
    case Int32Array:
    case Uint8Array:
    case Uint16Array:
    case Uint32Array:
    case Uint8ClampedArray:
    case Float32Array:
    case Float64Array:
      return Ia(e, r, t, n);
    case DataView:
      return Pa(e, r, t, n);
    case Map:
      return Ta(e, r, t, n);
    case Set:
      return Oa(e, r, t, n);
  }
  if (a === Promise || n instanceof Promise) return _a(e, r, t, n);
  let s = e.base.features;
  if (s & 32 && a === RegExp) return ze(t, n);
  if (s & 16) switch (a) {
    case BigInt64Array:
    case BigUint64Array:
      return Ra(e, r, t, n);
  }
  if (s & 1 && typeof AggregateError != "undefined" && (a === AggregateError || n instanceof AggregateError)) return xa(e, r, t, n);
  if (n instanceof Error) return ln(e, r, t, n);
  if (C in n || v in n) return Gr(e, r, t, n, !!a);
  throw new x(n);
}
__name(Ba, "Ba");
function Va(e, r, t, n) {
  if (Array.isArray(n)) return Aa(e, r, t, n);
  if (Xe(n)) return wa(e, r, t, n);
  if (Ze(n)) return Fa(e, r, t, n);
  let a = n.constructor;
  if (a === j) return E(e, r, n.replacement);
  let s = cn(e, r, t, n);
  return s || Ba(e, r, t, n, a);
}
__name(Va, "Va");
function Ma(e, r, t) {
  let n = Y(e.base, t);
  if (n.type !== 0) return n.value;
  let a = cn(e, r, n.value, t);
  if (a) return a;
  throw new x(t);
}
__name(Ma, "Ma");
function E(e, r, t) {
  if (r >= e.base.depthLimit) throw new Q(e.base.depthLimit);
  switch (typeof t) {
    case "boolean":
      return t ? H : J;
    case "undefined":
      return Ae;
    case "string":
      return $(t);
    case "number":
      return Oe(t);
    case "bigint":
      return we(t);
    case "object": {
      if (t) {
        let n = Y(e.base, t);
        return n.type === 0 ? Va(e, r + 1, n.value, t) : n.value;
      }
      return Ee;
    }
    case "symbol":
      return I(e.base, t);
    case "function":
      return Ma(e, r, t);
    default:
      throw new x(t);
  }
}
__name(E, "E");
function se(e, r) {
  e.state.initial ? e.state.buffer.push(r) : Xr(e, r, false);
}
__name(se, "se");
function $r(e, r) {
  if (e.state.onError) e.state.onError(r);
  else throw r instanceof z ? r : new z(r);
}
__name($r, "$r");
function fn(e) {
  e.state.onDone && e.state.onDone();
}
__name(fn, "fn");
function Xr(e, r, t) {
  try {
    e.state.onParse(r, t);
  } catch (n) {
    $r(e, n);
  }
}
__name(Xr, "Xr");
function Qr(e) {
  e.state.pending++;
}
__name(Qr, "Qr");
function be(e) {
  --e.state.pending <= 0 && fn(e);
}
__name(be, "be");
function W(e, r, t) {
  try {
    return E(e, r, t);
  } catch (n) {
    return $r(e, n), o;
  }
}
__name(W, "W");
function et(e, r) {
  let t = W(e, 0, r);
  t && (Xr(e, t, true), e.state.initial = false, La(e, e.state), e.state.pending <= 0 && Sr(e));
}
__name(et, "et");
function La(e, r) {
  for (let t = 0, n = r.buffer.length; t < n; t++) Xr(e, r.buffer[t], false);
}
__name(La, "La");
function Sr(e) {
  e.state.alive && (fn(e), e.state.alive = false);
}
__name(Sr, "Sr");
async function su(e, r = {}) {
  let t = A(r.plugins), n = te(2, { plugins: t, disabledFeatures: r.disabledFeatures, refs: r.refs });
  return await ne(n, e);
}
__name(su, "su");
function Sn(e, r) {
  let t = A(r.plugins), n = Jr({ plugins: t, refs: r.refs, disabledFeatures: r.disabledFeatures, onParse(a, s) {
    let i = lr({ plugins: t, features: n.base.features, scopeId: r.scopeId, markedRefs: n.base.marked }), u;
    try {
      u = fr(i, a);
    } catch (l) {
      r.onError && r.onError(l);
      return;
    }
    r.onSerialize(u, s);
  }, onError: r.onError, onDone: r.onDone });
  return et(n, e), Sr.bind(null, n);
}
__name(Sn, "Sn");
function iu(e, r) {
  let t = A(r.plugins), n = Jr({ plugins: t, refs: r.refs, disabledFeatures: r.disabledFeatures, depthLimit: r.depthLimit, onParse: r.onParse, onError: r.onError, onDone: r.onDone });
  return et(n, e), Sr.bind(null, n);
}
__name(iu, "iu");
function Pu(e, r = {}) {
  var i;
  let t = A(r.plugins), n = r.disabledFeatures || 0, a = (i = e.f) != null ? i : 63, s = Lt({ plugins: t, markedRefs: e.m, features: a & ~n, disabledFeatures: n });
  return sr(s, e.t);
}
__name(Pu, "Pu");
export {
  Pu as P,
  Sn as S,
  ai as a,
  dn as d,
  iu as i,
  re as r,
  su as s
};
