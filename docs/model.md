# Optimization model

## Problem

You have a set of courses, each with a fixed schedule, and $A$ accounts (2 by default). The
platform refuses to enroll **one account** in two courses whose schedules clash, but courses in
**different accounts** may clash freely. Choose which courses to take and in which account.

Ideally you take everything. When clashes make that impossible, the goal is lexicographic:
take as many priority-1 courses as possible; without losing any of them, as many priority-2
courses as possible; and so on. One priority-1 course is never traded for any number of
lower-priority courses.

## 1. Expanding courses into sessions

Each course has a start date, one or more weekly blocks (weekdays + start/end time) and a total
number of hours. Starting at the start date, walk forward day by day; on every day that matches a
block, create a session for it and add its length to the running total. Stop when the total
reaches the course hours, shortening the last session so the total is exact.

## 2. Clash graph

Two courses clash if any session of one overlaps any session of the other. Sessions are half-open
intervals: $[s_a, e_a)$ and $[s_b, e_b)$ overlap iff $s_a < e_b$ and $s_b < e_a$, so a session that
ends exactly when another starts is not a clash.

$E$ is the set of clashing course pairs $(i, j)$. Because each course's sessions are sorted,
checking a pair is a linear merge of both lists.

## 3. CP-SAT model

**Variables**

- $x_{i,a} \in \{0, 1\}$: course $i$ is taken in account $a$.

**Constraints**

- Each course in at most one account:
  $\sum_a x_{i,a} \le 1 \quad \forall i$
- No clashes inside an account:
  $x_{i,a} + x_{j,a} \le 1 \quad \forall (i, j) \in E,\ \forall a$

There is no constraint across different accounts, which is what allows clashing courses to be
taken in parallel.

## 4. Lexicographic objective

Let $N_p = \sum_{i : prio_i = p} \sum_a x_{i,a}$ be the number of priority-$p$ courses taken.
Maximize

$$\max \sum_p W_p N_p \qquad W_1 \gg W_2 \gg \dots$$

with weights large enough that one course of priority $p$ is worth more than every course of lower
priority combined.

## 5. Output

Courses per account, courses left out, and the clashing pairs. With `export-ics`, every session
becomes an iCalendar event (floating local time, so it appears in your calendar exactly as written).

## Possible extension: balancing accounts

Once priorities are maximized, a second criterion could spread courses evenly, e.g. maximize
$\min_a n_a$ or minimize $|n_1 - n_2|$. It is not part of the current model.
