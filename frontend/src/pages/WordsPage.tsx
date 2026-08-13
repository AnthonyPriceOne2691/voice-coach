import { useEffect, useState } from "react";

import { ListState } from "../components/ListState";
import { api } from "../lib/api";
import type { VocabularyItem } from "../types/api";

function WordCard({ item, onRemove }: { item: VocabularyItem; onRemove: () => void }) {
  return (
    <div className="word-card">
      <div className="word-head">
        <strong>{item.term_en}</strong>
        <span className="muted">
          {item.category}{" "}
          {item.times_seen && item.times_seen > 1 ? `· seen ×${item.times_seen}` : ""}
        </span>
        <button className="btn-link btn-danger" onClick={onRemove}>
          delete
        </button>
      </div>
      <div className="word-ru">{item.translation_ru}</div>
      <div className="muted">“{item.example_en}”</div>
    </div>
  );
}

export function WordsPage() {
  const [items, setItems] = useState<VocabularyItem[] | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      api
        .listVocabulary(query)
        .then(setItems)
        .catch(() => setError("Failed to load vocabulary."));
    }, 200);
    return () => window.clearTimeout(timer);
  }, [query]);

  const remove = async (id: string | undefined) => {
    if (!id) return;
    await api.deleteVocabulary(id);
    setItems((prev) => prev?.filter((item) => item.id !== id) ?? null);
  };

  return (
    <div>
      <h2>Useful Words</h2>
      <input
        className="search-input"
        placeholder="Search…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <ListState
        items={items}
        error={error}
        empty="Nothing here yet — words are added automatically after each review."
      >
        {(list) => (
          <>
            {list.map((item) => (
              <WordCard
                key={item.id ?? item.term_en}
                item={item}
                onRemove={() => void remove(item.id)}
              />
            ))}
            <p className="muted">Total: {list.length} words</p>
          </>
        )}
      </ListState>
    </div>
  );
}
