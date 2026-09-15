const GOODREADS_USER_ID = '166643433';
const GOODREADS_PROFILE_URL = 'https://www.goodreads.com/user/show/166643433-norman';
const BOOKS_TO_SHOW = 8;
const BAR_WIDTH = 24;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const PROXY_PREFIXES = [
    'https://cold-flower-83d6.normanbui23.workers.dev/?url=',
    'https://corsproxy.io/?url=',
    'https://api.allorigins.win/raw?url='
];

const domParser = typeof DOMParser === 'undefined' ? null : new DOMParser();

function shelfUrl(shelf) {
    const sort = shelf === 'read' ? '&sort=date_read&order=d' : '';
    return `https://www.goodreads.com/review/list_rss/${GOODREADS_USER_ID}?shelf=${shelf}${sort}`;
}

async function fetchFeed(url) {
    for (const prefix of PROXY_PREFIXES) {
        try {
            const response = await fetch(prefix + encodeURIComponent(url));
            if (response.ok) return await response.text();
        } catch (_) { /* try next proxy */ }
    }
    throw new Error('All proxies failed');
}

function tagText(item, tagName) {
    const element = item.getElementsByTagName(tagName)[0];
    return element ? element.textContent.trim() : '';
}

function parseItems(xml, status) {
    return [...domParser.parseFromString(xml, 'text/xml').getElementsByTagName('item')].map(item => {
        const bookId = tagText(item, 'book_id');
        return {
            title: tagText(item, 'title'),
            author: tagText(item, 'author_name'),
            url: bookId ? `https://www.goodreads.com/book/show/${bookId}` : GOODREADS_PROFILE_URL,
            pages: Number.parseInt(tagText(item, 'num_pages'), 10) || 0,
            rating: Number.parseInt(tagText(item, 'user_rating'), 10) || 0,
            publishedYear: Number.parseInt(tagText(item, 'book_published'), 10) || null,
            readAt: tagText(item, 'user_read_at'),
            status
        };
    });
}

/** One text bar chart: rows of `label  ####  value`, sized against the largest row. */
export function chartText(title, rows) {
    const max = Math.max(...rows.map(row => row.value), 1);
    const labelWidth = Math.max(...rows.map(row => row.label.length));
    const body = rows.map(row => {
        const filled = row.value ? Math.max(1, Math.round((row.value / max) * BAR_WIDTH)) : 0;
        const bar = '#'.repeat(filled).padEnd(BAR_WIDTH);
        return `${row.label.padEnd(labelWidth)}  ${bar}  ${row.value.toLocaleString()}`;
    }).join('\n');

    return `${title}\n\n${body}`;
}

function barChart(title, rows) {
    if (!rows.length) return null;

    const chart = document.createElement('pre');
    chart.textContent = chartText(title, rows);
    return chart;
}

function truncate(text, limit) {
    return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function buildCharts(finished, allBooks, year) {
    const readThisYear = finished.filter(book => book.readAt && new Date(book.readAt).getFullYear() === year);

    const monthly = new Array(12).fill(0);
    readThisYear.forEach(book => {
        const month = new Date(book.readAt).getMonth();
        if (!Number.isNaN(month)) monthly[month] += 1;
    });

    const rated = finished.filter(book => book.rating > 0);
    const ratings = rated.length
        ? [5, 4, 3, 2, 1].map(stars => ({
            label: `${stars} star`,
            value: rated.filter(book => book.rating === stars).length
        }))
        : [];

    const decades = Object.entries(allBooks.reduce((counts, book) => {
        if (!book.publishedYear) return counts;
        const decade = Math.floor(book.publishedYear / 10) * 10;
        counts[decade] = (counts[decade] || 0) + 1;
        return counts;
    }, {}))
        .sort(([left], [right]) => Number(left) - Number(right))
        .map(([decade, count]) => ({ label: `${decade}s`, value: count }));

    const recentPages = finished
        .filter(book => book.pages > 0)
        .slice(0, 6)
        .map(book => ({ label: truncate(book.title, 28), value: book.pages }));

    return [
        barChart(`Books read by month, ${year}`, monthly.map((count, index) => ({ label: MONTHS[index], value: count }))),
        barChart('Ratings given', ratings),
        barChart('Publication decade', decades),
        barChart('Pages per recent read', recentPages)
    ].filter(Boolean);
}

function bookListItem(book) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = book.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = book.title;
    item.append(link, ` by ${book.author} (${book.status})`);
    return item;
}

async function loadBooks() {
    const statsElement = document.getElementById('reading-stats');
    const chartsElement = document.getElementById('reading-charts');
    const list = document.getElementById('books');
    if (!statsElement || !chartsElement || !list) return;

    try {
        const [readingXml, readXml] = await Promise.all([
            fetchFeed(shelfUrl('currently-reading')),
            fetchFeed(shelfUrl('read'))
        ]);

        const reading = parseItems(readingXml, 'Reading');
        const finished = parseItems(readXml, 'Read');
        const year = new Date().getFullYear();
        const readThisYear = finished.filter(book => book.readAt && new Date(book.readAt).getFullYear() === year);
        const pagesThisYear = readThisYear.reduce((total, book) => total + book.pages, 0);
        const ratedThisYear = readThisYear.filter(book => book.rating > 0);
        const averageRating = ratedThisYear.length
            ? (ratedThisYear.reduce((total, book) => total + book.rating, 0) / ratedThisYear.length).toFixed(1)
            : null;

        statsElement.textContent = [
            `${readThisYear.length} books in ${year}`,
            pagesThisYear ? `${pagesThisYear.toLocaleString()} pages` : null,
            averageRating ? `avg. rating ${averageRating}/5` : null
        ].filter(Boolean).join(' · ');

        chartsElement.replaceChildren(...buildCharts(finished, [...reading, ...finished], year));
        list.replaceChildren(...[...reading, ...finished].slice(0, BOOKS_TO_SHOW).map(bookListItem));
    } catch (error) {
        console.error('Failed to load books from Goodreads:', error);
        statsElement.textContent = 'Could not load reading data.';
    }
}

if (typeof document !== 'undefined') loadBooks();
