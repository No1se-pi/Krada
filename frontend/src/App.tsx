import { type FormEvent, type ReactNode, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api, type Dashboard, type GameClass, type Raid, type Result } from './api';

const glyphs: Record<string, string> = {
  smith: '⚒',
  mage: '✦',
  poet: '❧',
  knight: '♜',
  druid: '☘',
  alchemist: '⚗',
};

export function App() {
  const queryClient = useQueryClient();
  const [loggedIn, setLoggedIn] = useState(api.hasSession());
  const [platformError, setPlatformError] = useState('');

  useEffect(() => {
    // MAX owns initData. The client forwards the opaque string; only the backend may trust it
    // after signature and freshness validation.
    if (!loggedIn && window.WebApp?.initData) {
      api
        .loginMax(window.WebApp.initData)
        .then(() => setLoggedIn(true))
        .catch((error: unknown) =>
          setPlatformError(error instanceof Error ? error.message : 'Ошибка входа через MAX'),
        );
    }
  }, [loggedIn]);

  const dashboard = useQuery({ queryKey: ['me'], queryFn: api.me, enabled: loggedIn });

  if (!loggedIn) {
    return <Login error={platformError} onDone={() => setLoggedIn(true)} />;
  }
  if (dashboard.isLoading) {
    return (
      <Shell>
        <p className="eyebrow">Разжигаем очаг…</p>
        <div className="skeleton" />
      </Shell>
    );
  }
  if (dashboard.error) {
    return (
      <Shell>
        <p className="error">{dashboard.error.message}</p>
        <button
          onClick={() => {
            api.logout();
            setLoggedIn(false);
          }}
        >
          Войти заново
        </button>
      </Shell>
    );
  }
  if (!dashboard.data?.character) {
    return (
      <CreateHero onDone={() => queryClient.invalidateQueries({ queryKey: ['me'] })} />
    );
  }
  return (
    <Home
      data={dashboard.data}
      refresh={() => queryClient.invalidateQueries({ queryKey: ['me'] })}
    />
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <main>
      <header>
        <span className="brand-mark">К</span>
        <div>
          <b>КРАДА</b>
          <small>хроники живого огня</small>
        </div>
      </header>
      {children}
    </main>
  );
}

function Login({ onDone, error }: { onDone: () => void; error: string }) {
  const [name, setName] = useState('Добрыня');
  const login = useMutation({ mutationFn: () => api.login(name), onSuccess: onDone });

  return (
    <Shell>
      <section className="hero">
        <span className="rune">ᛟ</span>
        <p className="eyebrow">Образовательная RPG</p>
        <h1>
          Зажги огонь
          <br />
          <i>знаний</i>
        </h1>
        <p>Войди в земли Крады, собери героя и одолей тени невежества.</p>
      </section>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          login.mutate();
        }}
      >
        <label>
          Имя странника
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            minLength={2}
            maxLength={80}
            required
          />
        </label>
        <button disabled={login.isPending}>
          Войти в летопись <span>→</span>
        </button>
        {(error || login.error) && <p className="error">{error || login.error?.message}</p>}
        <small className="hint">
          Локальный режим · MAX подключится автоматически внутри приложения
        </small>
      </form>
    </Shell>
  );
}

function CreateHero({ onDone }: { onDone: () => void }) {
  const classes = useQuery({ queryKey: ['classes'], queryFn: api.classes });
  const [chosen, setChosen] = useState('mage');
  const [name, setName] = useState('Ратибор');
  const create = useMutation({
    mutationFn: () => api.createCharacter(name, chosen),
    onSuccess: onDone,
  });

  return (
    <Shell>
      <p className="eyebrow">Шаг I · Призвание</p>
      <h1>Кем ты станешь?</h1>
      <p className="muted">Выбор меняет стиль приключений, но не силу твоих знаний.</p>
      <div className="class-grid">
        {classes.data?.map((gameClass: GameClass) => (
          <button
            type="button"
            className={`class-card ${chosen === gameClass.key ? 'selected' : ''}`}
            onClick={() => setChosen(gameClass.key)}
            key={gameClass.key}
          >
            <span>{glyphs[gameClass.key]}</span>
            <b>{gameClass.title}</b>
            <small>{gameClass.description}</small>
          </button>
        ))}
      </div>
      <form
        onSubmit={(event: FormEvent) => {
          event.preventDefault();
          create.mutate();
        }}
      >
        <label>
          Имя героя
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            minLength={2}
            maxLength={40}
            required
          />
        </label>
        <button disabled={create.isPending}>Принять призвание</button>
        {create.error && <p className="error">{create.error.message}</p>}
      </form>
    </Shell>
  );
}

function Home({ data, refresh }: { data: Dashboard; refresh: () => void }) {
  // The dashboard includes an active raid so WebView suspension does not lose server state.
  const [raid, setRaid] = useState<Raid | null>(data.active_raid);
  const [result, setResult] = useState<Result | null>(null);
  const start = useMutation({
    mutationFn: api.startRaid,
    onSuccess: (createdRaid) => {
      setRaid(createdRaid);
      setResult(null);
    },
  });
  const answer = useMutation({
    mutationFn: (value: string) => api.answer(raid!.id, value),
    onSuccess: (raidResult) => {
      setResult(raidResult);
      setRaid(null);
      refresh();
    },
  });
  const character = data.character!;

  return (
    <Shell>
      <section className="profile">
        <div className="avatar">
          <span>{glyphs[character.class_key]}</span>
        </div>
        <div>
          <p className="eyebrow">
            {data.school_name} · {data.class_name}
          </p>
          <h2>{character.name}</h2>
          <p>
            Уровень {character.level} · {character.xp} опыта
          </p>
        </div>
      </section>
      <div className="stats">
        <article>
          <small>Искры</small>
          <strong>◆ {data.embers}</strong>
        </article>
        <article>
          <small>Слава школы</small>
          <strong>{data.school_score}</strong>
        </article>
      </div>
      {raid ? (
        <RaidView raid={raid} pending={answer.isPending} answer={(value) => answer.mutate(value)} />
      ) : result ? (
        <ResultView result={result} again={() => start.mutate()} />
      ) : (
        <section className="quest">
          <p className="eyebrow">Доступное испытание</p>
          <h2>Тень над древней летописью</h2>
          <p>История · одно испытание · награда до 15 искр</p>
          <button onClick={() => start.mutate()} disabled={start.isPending}>
            Начать рейд <span>⚔</span>
          </button>
        </section>
      )}
      {(start.error || answer.error) && (
        <p className="error">{start.error?.message || answer.error?.message}</p>
      )}
      <nav>
        <span className="active">
          ⌂<small>Очаг</small>
        </span>
        <span>
          ♜<small>Рейтинг</small>
        </span>
        <span>
          ☷<small>Сумка</small>
        </span>
      </nav>
    </Shell>
  );
}

function RaidView({
  raid,
  answer,
  pending,
}: {
  raid: Raid;
  answer: (value: string) => void;
  pending: boolean;
}) {
  if (!raid.question) {
    return (
      <section className="quest raid">
        <p className="eyebrow">Состояние обновилось</p>
        <h2>Испытание уже завершено</h2>
        <p>Вернитесь к очагу, чтобы получить актуальное состояние.</p>
      </section>
    );
  }
  return (
    <section className="quest raid">
      <p className="eyebrow">{raid.question.subject} · испытание I</p>
      <h2>{raid.question.text}</h2>
      <div className="answers">
        {raid.question.options.map((value) => (
          <button disabled={pending} key={value} onClick={() => answer(value)}>
            {value}
          </button>
        ))}
      </div>
    </section>
  );
}

function ResultView({ result, again }: { result: Result; again: () => void }) {
  return (
    <section className={`quest result ${result.correct ? 'win' : ''}`}>
      <span className="result-rune">{result.correct ? '✦' : '☾'}</span>
      <p className="eyebrow">Рейд завершён</p>
      <h2>{result.correct ? 'Летопись спасена' : 'Знание крепнет'}</h2>
      <p>{result.explanation}</p>
      <div className="reward">
        <b>+{result.xp_awarded} опыта</b>
        <b>+{result.embers_awarded} ◆</b>
      </div>
      <button onClick={again}>Новое испытание</button>
    </section>
  );
}
