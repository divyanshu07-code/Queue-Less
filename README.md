# QueueLess

> 🏆 Built for **Hack Devengers 1.0 — Open Innovation Challenge**

QueueLess is a smart virtual queue management platform designed to eliminate unnecessary physical waiting at campus services such as the **College Office, Canteen, Clinic, and Library**.

Students can take a digital token from their phone, leave the physical queue, track their live position and estimated waiting time, and receive notifications when their turn is approaching.

Staff get a real-time admin dashboard to manage queues, monitor service demand, and make better operational decisions.

---

## 🚀 Live Demo

🌐 **[Try QueueLess Live](https://queue-less.onrender.com)**

💻 **[View Source Code on GitHub](https://github.com/divyanshu07-code/Queue-Less)**

> **Take a token. Leave the physical queue. Get your time back.**

---

## 💡 Problem

Students often waste significant time physically standing in queues for campus services without knowing:

- How many people are ahead
- How long they will have to wait
- When they should return
- Whether the queue is becoming crowded

This creates unnecessary waiting, congestion, and inefficient use of students' time.

---

## 💡 Solution

QueueLess transforms physical campus queues into a **digital, real-time queue system**.

Instead of standing in line, students can:

1. Select a campus service
2. Take a digital token
3. Leave the physical queue
4. Track their live position
5. See an estimated waiting time
6. Receive an "almost your turn" notification
7. Receive an "it's your turn" notification
8. Return to the counter when needed

Meanwhile, administrators get real-time visibility into queue demand and service performance.

---

## ✨ Features

### 🎟️ Student Experience

- **Digital tokens** — join any counter's line in two taps.
- **No account required** — students can join without creating an account.
- **Live queue position** — see how many people are ahead.
- **Estimated waiting time** — dynamically calculated from actual service history.
- **Ticket recovery** — closing the browser tab does not immediately lose the active ticket.
- **"You're almost up" notification** — triggered when only two people are ahead.
- **"It's your turn" notification** — triggered when an administrator calls the student's token.
- **Duplicate-join protection** — prevents multiple active tickets for the same person at the same counter.
- **Responsive design** — works across desktop, tablet, and mobile.

---

### 🧠 Queue Intelligence

QueueLess provides administrators with real-time queue insights.

For every counter, the system calculates:

- Current queue size
- Traffic level:
  - Clear
  - Low
  - Moderate
  - High
- Estimated time to clear the queue
- Operational recommendations

For example:

> **High Traffic Detected**  
> Consider opening an additional counter.

The recommendations are calculated from the counter's queue state and service history rather than being hardcoded.

---

### 📊 Impact Metrics

The home page displays campus-wide impact metrics including:

- Tokens served
- Estimated minutes saved for students
- Current queue activity

The goal is to demonstrate the real-world value of replacing physical waiting with predictable digital waiting.

---

### 🛠️ Admin Dashboard

Staff can manage each campus service from a centralized dashboard.

Administrators can:

- Call the next token
- Mark walk-ins as served
- Skip no-shows
- Send skipped tickets to the back of the queue
- Reset a counter
- Monitor current queue activity
- View live statistics
- View Queue Intelligence
- Monitor service performance

The dashboard refreshes automatically so staff can manage queues in real time.

---

### 📺 Public Now-Serving Board

The home page provides a live overview of all campus counters.

Students can see which token is currently being served at:

- 🏢 College Office
- 🍔 Canteen
- 🏥 Clinic
- 📚 Library

This can also be displayed on a shared campus screen.

---

### 🌗 Modern Responsive UI

- Desktop and mobile responsive
- Light/dark theme
- Mobile-friendly service navigation
- Real-time queue cards
- Digital ticket-style interface
- LED-inspired "Now Serving" display
- Designed for quick use in real campus environments

---

# 🏗️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend logic |
| Flask | Web framework and API |
| SQLite | Database |
| HTML5 | Page structure |
| CSS3 | Responsive UI |
| JavaScript | Real-time frontend interactions |
| Gunicorn | Production WSGI server |
| Render | Cloud deployment |

---

# 📂 Project Structure

```text
Queue-Less/
│
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
│
├── templates/
│   ├── index.html
│   ├── student.html
│   ├── admin.html
│   ├── admin_login.html
│   ├── 404.html
│   └── _icons.html
│
└── static/
    ├── css/
    │   └── style.css
    │
    └── js/
        ├── main.js
        ├── home.js
        ├── student.js
        └── admin.js
