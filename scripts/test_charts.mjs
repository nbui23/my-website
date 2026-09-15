import assert from 'node:assert/strict';
import { chartText } from './main.js';

const chart = chartText('Ratings given', [
    { label: '5 star', value: 4 },
    { label: '4 star', value: 2 },
    { label: '3 star', value: 0 }
]);
const [title, blank, ...rows] = chart.split('\n');

assert.equal(title, 'Ratings given');
assert.equal(blank, '');
assert.equal(rows.length, 3);

// Largest row fills the bar, half the value fills half of it, zero draws nothing.
assert.equal(rows[0], '5 star  ########################  4');
assert.equal(rows[1], '4 star  ############              2');
assert.equal(rows[2], '3 star                            0');

// Labels pad to the widest one so the bars line up.
const padded = chartText('t', [{ label: 'a', value: 1 }, { label: 'bbb', value: 1 }]).split('\n');
assert.equal(padded[2].indexOf('#'), padded[3].indexOf('#'));

// A single zero row must not divide by zero or emit a bar.
assert.equal(chartText('t', [{ label: 'x', value: 0 }]).split('\n')[2], `x${' '.repeat(28)}0`);

console.log('chart tests OK');
