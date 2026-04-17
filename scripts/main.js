const tabs = [...document.querySelectorAll('.tab')];
const tabContents = [...document.querySelectorAll('.tab-content')];
const tabIndicator = document.querySelector('.tab-indicator');

const BOOK_PROXY_PREFIXES = [
    'https://corsproxy.io/?url=',
    'https://api.allorigins.win/raw?url='
];
const GOODREADS_USER_ID = '166643433';
const GOODREADS_PROFILE_URL = 'https://www.goodreads.com/user/show/166643433-norman';
const BOOKS_TO_SHOW = 5;
const RECENT_PAGE_BOOKS_TO_SHOW = 6;
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const domParser = new DOMParser();

function getShelfUrl(shelf) {
    return `https://www.goodreads.com/review/list_rss/${GOODREADS_USER_ID}?shelf=${shelf}${shelf === 'read' ? '&sort=date_read&order=d' : ''}`;
}

function updateTabIndicator(activeTab) {
    if (!tabIndicator) return;
    tabIndicator.style.left = `${activeTab.offsetLeft}px`;
    tabIndicator.style.width = `${activeTab.offsetWidth}px`;
}

function setActiveTab(tab) {
    const targetSection = document.getElementById(tab.dataset.tab);
    if (!targetSection) return;

    tabs.forEach(button => button.classList.remove('active'));
    tabContents.forEach(section => section.classList.remove('active'));

    tab.classList.add('active');
    targetSection.classList.add('active');
    updateTabIndicator(tab);
}

function initTabs() {
    if (!tabs.length || !tabIndicator) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', () => setActiveTab(tab));
    });

    const activeTab = document.querySelector('.tab.active') || tabs[0];
    if (activeTab) {
        setActiveTab(activeTab);
    }

    window.addEventListener('resize', () => {
        const currentTab = document.querySelector('.tab.active');
        if (currentTab) updateTabIndicator(currentTab);
    });
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

async function fetchRssFeed(url) {
    for (const proxyPrefix of BOOK_PROXY_PREFIXES) {
        try {
            const response = await fetch(proxyPrefix + encodeURIComponent(url));
            if (response.ok) return await response.text();
        } catch (_) {}
    }

    throw new Error('All proxies failed');
}

function getTagText(item, tagName) {
    const element = item.getElementsByTagName(tagName)[0];
    return element ? element.textContent.trim() : '';
}

function normalizeCoverUrl(url) {
    return url.replace(/\._S[XY]\d+_(?=\.jpg)/i, '');
}

function getBookUrl(item) {
    const description = getTagText(item, 'description');
    if (description) {
        const descriptionDocument = domParser.parseFromString(description, 'text/html');
        const link = descriptionDocument.querySelector('a[href]');
        if (link?.href) return link.href;
    }

    const bookId = getTagText(item, 'book_id');
    return bookId ? `https://www.goodreads.com/book/show/${bookId}` : GOODREADS_PROFILE_URL;
}

function dedupeBooks(books) {
    const booksById = new Map();

    books.forEach(book => {
        const key = book.bookId || `${book.title}::${book.author}`;
        if (!booksById.has(key)) {
            booksById.set(key, book);
        }
    });

    return [...booksById.values()];
}

function renderMonthlyChart(monthlyCounts, currentYear, currentMonth) {
    const maxCount = Math.max(...monthlyCounts, 1);

    return `
        <section class="chart-card chart-card-wide">
            <div class="chart-title">Books Read by Month — ${currentYear}</div>
            <div class="chart-bars">
                ${monthlyCounts.map((count, index) => {
                    const height = count ? Math.max((count / maxCount) * 100, 6) : 0;
                    const futureClass = index > currentMonth ? ' chart-future' : '';

                    return `
                        <div class="chart-col${futureClass}">
                            <div class="chart-bar-wrap">
                                <div class="chart-bar" style="height:${height}%"></div>
                            </div>
                            <div class="chart-count">${count || ''}</div>
                            <div class="chart-month">${MONTH_NAMES[index]}</div>
                        </div>
                    `;
                }).join('')}
            </div>
        </section>
    `;
}

function renderHorizontalBarChart({
    title,
    items,
    valueFormatter = value => value,
    wide = false,
    rowClass = '',
    linkRows = false,
    emptyMessage = 'No data yet.'
}) {
    const maxValue = Math.max(...items.map(item => item.value), 1);

    return `
        <section class="chart-card${wide ? ' chart-card-wide' : ''}">
            <div class="chart-title">${title}</div>
            ${items.length ? `
                <div class="horizontal-bars">
                    ${items.map(item => {
                        const isLinkRow = linkRows && item.url;
                        const width = item.value ? Math.max((item.value / maxValue) * 100, 6) : 0;
                        const rowTag = isLinkRow ? 'a' : 'div';
                        const rowClasses = ['horizontal-row', rowClass, isLinkRow ? 'horizontal-row-link' : '']
                            .filter(Boolean)
                            .join(' ');
                        const rowAttributes = isLinkRow
                            ? ` href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer"`
                            : '';

                        return `
                            <${rowTag} class="${rowClasses}"${rowAttributes}>
                                <div class="horizontal-label" title="${escapeHtml(item.label)}">${escapeHtml(item.label)}</div>
                                <div class="horizontal-track">
                                    <div class="horizontal-fill" style="width:${width}%"></div>
                                </div>
                                <div class="horizontal-value">${escapeHtml(valueFormatter(item.value, item))}</div>
                            </${rowTag}>
                        `;
                    }).join('')}
                </div>
            ` : `<div class="chart-empty">${emptyMessage}</div>`}
        </section>
    `;
}

function parseFeedItems(xmlDocument, status) {
    return [...xmlDocument.getElementsByTagName('item')].map(item => ({
        bookId: getTagText(item, 'book_id'),
        title: getTagText(item, 'title'),
        author: getTagText(item, 'author_name'),
        cover: normalizeCoverUrl(getTagText(item, 'book_image_url')),
        url: getBookUrl(item),
        pages: Number.parseInt(getTagText(item, 'num_pages'), 10) || 0,
        rating: Number.parseInt(getTagText(item, 'user_rating'), 10) || 0,
        publishedYear: Number.parseInt(getTagText(item, 'book_published'), 10) || null,
        readAt: getTagText(item, 'user_read_at'),
        status
    }));
}

function renderReadingStats(statsElement, currentYearBooks, currentYear, currentYearPages, averageRating) {
    statsElement.innerHTML = [
        { value: currentYearBooks.length, label: `Books in ${currentYear}` },
        currentYearPages > 0 ? { value: currentYearPages.toLocaleString(), label: `Pages in ${currentYear}` } : null,
        averageRating ? { value: `${averageRating} / 5`, label: 'Avg. Rating' } : null
    ]
        .filter(Boolean)
        .map(stat => `
            <div class="stat-item">
                <span class="stat-value">${stat.value}</span>
                <span class="stat-label">${stat.label}</span>
            </div>
        `)
        .join('');
}

async function loadBooks() {
    const statsElement = document.getElementById('reading-stats');
    const chartsElement = document.getElementById('reading-charts');
    const booksGrid = document.getElementById('books-grid');

    if (!statsElement || !chartsElement || !booksGrid) return;

    try {
        const [currentlyReadingXml, readShelfXml] = await Promise.all([
            fetchRssFeed(getShelfUrl('currently-reading')),
            fetchRssFeed(getShelfUrl('read'))
        ]);

        const currentlyReadingBooks = parseFeedItems(domParser.parseFromString(currentlyReadingXml, 'text/xml'), 'reading');
        const finishedBooks = parseFeedItems(domParser.parseFromString(readShelfXml, 'text/xml'), 'read');
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentYearBooks = finishedBooks.filter(book => book.readAt && new Date(book.readAt).getFullYear() === currentYear);
        const currentYearPages = currentYearBooks.reduce((pageTotal, book) => pageTotal + book.pages, 0);
        const ratedCurrentYearBooks = currentYearBooks.filter(book => book.rating > 0);
        const averageRating = ratedCurrentYearBooks.length
            ? (ratedCurrentYearBooks.reduce((ratingTotal, book) => ratingTotal + book.rating, 0) / ratedCurrentYearBooks.length).toFixed(1)
            : null;

        renderReadingStats(statsElement, currentYearBooks, currentYear, currentYearPages, averageRating);

        const monthlyCounts = new Array(12).fill(0);
        currentYearBooks.forEach(book => {
            const month = new Date(book.readAt).getMonth();
            if (!Number.isNaN(month)) monthlyCounts[month] += 1;
        });

        const currentMonth = currentDate.getMonth();
        const ratedAllTimeBooks = finishedBooks.filter(book => book.rating > 0);
        const ratingDistribution = ratedAllTimeBooks.length
            ? [5, 4, 3, 2, 1].map(stars => ({
                label: `${stars}★`,
                value: ratedAllTimeBooks.filter(book => book.rating === stars).length
            }))
            : [];

        const publicationDecades = Object.entries(
            dedupeBooks([...currentlyReadingBooks, ...finishedBooks]).reduce((counts, book) => {
                if (!book.publishedYear) return counts;
                const decade = Math.floor(book.publishedYear / 10) * 10;
                counts[decade] = (counts[decade] || 0) + 1;
                return counts;
            }, {})
        )
            .sort((left, right) => Number(left[0]) - Number(right[0]))
            .map(([decade, count]) => ({
                label: `${decade}s`,
                value: count
            }));

        const recentPageBooks = finishedBooks
            .filter(book => book.pages > 0)
            .slice(0, RECENT_PAGE_BOOKS_TO_SHOW)
            .map(book => ({
                label: book.title,
                value: book.pages,
                url: book.url
            }));

        chartsElement.innerHTML = [
            renderMonthlyChart(monthlyCounts, currentYear, currentMonth),
            renderHorizontalBarChart({
                title: 'Rating Distribution — All Time',
                items: ratingDistribution
            }),
            renderHorizontalBarChart({
                title: 'Publication Decade',
                items: publicationDecades
            }),
            renderHorizontalBarChart({
                title: `Pages per Recent Read${recentPageBooks.length ? ` — Last ${recentPageBooks.length}` : ''}`,
                items: recentPageBooks,
                valueFormatter: value => `${value.toLocaleString()} pp`,
                wide: true,
                linkRows: true,
                rowClass: 'book-row'
            })
        ].join('');

        const visibleBooks = [...currentlyReadingBooks, ...finishedBooks].slice(0, BOOKS_TO_SHOW);
        if (!visibleBooks.length) return;

        booksGrid.innerHTML = visibleBooks.map(book => `
            <a href="${escapeHtml(book.url)}" target="_blank" rel="noopener noreferrer" class="book-card">
                <div class="book-cover">
                    <img src="${escapeHtml(book.cover)}" alt="${escapeHtml(book.title)}" loading="lazy">
                </div>
                <div class="book-info">
                    <span class="book-status ${book.status}">${book.status === 'reading' ? 'Reading' : 'Read'}</span>
                    <p class="book-title">${escapeHtml(book.title)}</p>
                    <p class="book-author">${escapeHtml(book.author)}</p>
                </div>
            </a>
        `).join('');
    } catch (error) {
        console.error('Failed to load books from Goodreads:', error);
    }
}

window.addEventListener('load', () => {
    initTabs();
    loadBooks();
});
