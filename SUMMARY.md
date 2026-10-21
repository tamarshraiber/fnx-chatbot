# Phoenix (fnx.co.il) Hebrew chatbot - short summary

A Hebrew chatbot that answers only from the public pages of fnx.co.il. It always shows the page it used, and when the
answer is not on the website it says so and sends the user to customer service. The main goal is no made-up answers.

## How the data was collected
- The page list comes from the website's sitemap (1,643 URLs). We keep only the useful sections: claims, customer
  service, insurance products and their information pages, savings and pensions (1,143 pages).
- Pages blocked by `robots.txt`, login and form sites, and English pages are skipped. We wait 1.5 seconds between
  requests.
- The pages are fetched once and stored. The website is never contacted while a user asks a question.

## How the text is chosen and cut (chunks)
- Each page is cleaned first: cookie banner, images, link addresses and the shared footer are removed.
- The text is split by headings into pieces of about 800 characters (small overlap, very short pieces are merged with a
  neighbour). Every piece keeps the page title, URL and date, so the answer can name its source.
- A short hand-written contact summary is added to the contact pages, because the real page is mostly menus.

## How an answer is made
1. A follow-up question is rewritten into a full question using the last messages.
2. The question is turned into numbers by `multilingual-e5-base`, a model that runs on our own server (no quota, no cost).
3. The closest pieces are found in Supabase (pgvector). Pieces below a similarity cutoff (0.80) are dropped, duplicates
   are removed, and the pieces that follow the best ones on the same page are added.
4. Gemini writes a short Hebrew answer from those pieces only. The cited URL must be one of the retrieved pages,
   otherwise the answer becomes "not on the website". If Gemini fails, Groq and then OpenRouter are used.
5. The answer is streamed to the React page. Questions about a personal policy or professional advice get a general
   explanation and a referral to customer service.

## Results (30 test questions: 20 answerable, 10 not answerable)
- Retrieval alone finds the expected page in the top 5 for 20 of 20 answerable questions.
- Full answers: 19 of 20 answerable questions answered with a correct page; 7 of 10 unanswerable questions correctly
  refused. The 3 misses are borderline: the site does have articles on those topics.
- 195 backend tests and 31 frontend tests pass.

## Limitations
- Between refreshes the bot may show old information.
- The cutoff is low on purpose, so that real questions are not refused. Because of that, a question close to the
  website's topics can get an answer built from a loosely related page.
- The test set is small (30 questions), so the numbers show a direction, not a guarantee.
- A few pages were empty or could not be fetched (1,075 of the 1,143 selected pages are in the database).
- The free servers (Render, Gemini free tier) can be slow to wake up or hit rate limits; the backup models help but
  can answer in a slightly different style.
- Chat history lives only in the browser; nothing is saved on the server.

## Refresh process
- One command, `python -m backend.ingestion.run`, compares the sitemap with what we hold. It crawls only new or changed
  pages, embeds only pages whose text changed, and can continue after a stop.
- A page is deleted only if the website itself answers 404 or 410. If the sitemap suddenly looks far smaller, nothing
  is deleted.
- Every run saves a report of added, updated, removed and failed pages.
- A GitHub Actions job runs the same command every Sunday, and can also be started by hand.

## Run it
See `README.md`. Backend: `uvicorn backend.main:app`. Frontend: `cd frontend && npm install && npm run dev`.
