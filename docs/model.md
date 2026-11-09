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

$E$ is the set of clashing course pairs $(i, j)$. Checking a pair is one pass over both courses'
sessions in start order, remembering the latest end seen on each side; this also handles a course
whose own blocks overlap (two blocks on the same day).

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

$$\max \sum_p W_p N_p$$

with weights large enough that one course of priority $p$ is worth more than every course of lower
priority combined. The smallest such integer weights are computed from the number of courses
$C_q$ at each level, walking from the least important level upwards:

$$W_p = 1 + \sum_{q \text{ less important than } p} W_q \, C_q$$

For example, with three priority-1 courses, one priority-2 course and two priority-3 courses the
weights are $W_3 = 1$, $W_2 = 1 + 2 \cdot 1 = 3$ and $W_1 = 1 + 2 \cdot 1 + 1 \cdot 3 = 6$. Only levels
that occur get a weight, so gaps such as priorities 1, 5 and 15 do not inflate them.

With very many courses or levels these weights can grow beyond what is safe for the solver
($2^{53}$). In that case the problem is solved **level by level** instead: maximize $N_1$, add the
constraint $N_1 \ge N_1^*$, maximize $N_2$, and so on, reusing each solution as a hint for the next
stage. Both methods give the same number of courses per priority.

## 5. Symmetry and reproducibility

Accounts are interchangeable, so every assignment has copies that only swap account labels.
The model numbers accounts by their lowest course index (course $i$ may only use accounts
$1 \dots i+1$), which removes those copies.

Several assignments can still be equally good. The solver runs its search strategies in a fixed,
interleaved order instead of racing them in parallel, so the same input always gives the same
result, provided it finishes within the time limit. For realistic inputs (up to ~50 courses)
this takes well under two seconds.

## 6. Output

Courses per account, courses left out, and the clashing pairs. With `export-ics`, every session
becomes an iCalendar event (floating local time, so it appears in your calendar exactly as written).

## 7. Possible extension: balancing accounts

Once priorities are maximized, a second criterion could spread courses evenly, e.g. maximize
$\min_a n_a$ or minimize $|n_1 - n_2|$. It is not part of the current model.
