import { createHash } from "crypto";
import NodeCache from "node-cache";

const cache = new NodeCache({ stdTTL: 3600 }); // TTL de 1 hora

function normalizeQuestion(question) {
  return question.toLowerCase().trim().replace(/\s+/g, " ");
}

function makeKey(question) {
  return createHash("md5").update(normalizeQuestion(question)).digest("hex");
}

export function getFromCache(question) {
  const key = makeKey(question);
  return cache.get(key) || null;
}

export function setInCache(question, value) {
  const key = makeKey(question);
  cache.set(key, value);
}

export function getCacheStats() {
  return cache.getStats();
}
