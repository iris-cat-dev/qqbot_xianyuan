'use strict';

class InvalidReviewError extends Error {
  constructor(message) {
    super(message);
    this.name = 'InvalidReviewError';
  }
}

function exactObject(value, keys, label) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)
    || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) {
    throw new InvalidReviewError(`${label}必须是 JSON 对象。`);
  }
  const actual = Reflect.ownKeys(value);
  if (actual.length !== keys.length || keys.some(key => !Object.hasOwn(value, key))
    || actual.some(key => !keys.includes(key))) {
    throw new InvalidReviewError(`${label}字段不符合判定格式。`);
  }
}

function boundedText(value, maximum, label) {
  if (typeof value !== 'string' || !value.trim() || [...value].length > maximum) {
    throw new InvalidReviewError(`${label}必须是非空且不超过${maximum}字的文字。`);
  }
}

module.exports = { InvalidReviewError, exactObject, boundedText };
