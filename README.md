# Hospital Emergency & Patient Priority Management System

An enterprise-grade, college Data Structures & Algorithms (DSA) capstone project implementing a real-time emergency room triage and patient priority management system.

Built with **Python 3.11+**, **FastAPI**, **MySQL**, and a responsive **Vanilla HTML5/CSS3/JavaScript** frontend.

---


- **GitHub Repository:** [https://github.com/arpitSH03/hospital-priority-system](https://github.com/arpitSH03/hospital-priority-system)
- **Cloud Deployment Guide:** Deployed in 1 click on [Render.com](https://render.com) or [Railway.app](https://railway.app) 

---

## 1. Problem Statement

Traditional First-Come, First-Served (FCFS) hospital intake systems are fundamentally unsuited for Emergency Departments (ED). In acute clinical settings, medical severity must strictly dictate treatment order rather than arrival time; a patient presenting with an acute myocardial infarction (heart attack) cannot wait behind a patient with a minor ankle sprain.

Furthermore, naive software implementations—such as continuously re-sorting an array upon each arrival ($O(N \log N)$ or $O(N^2)$) or scanning linearly to extract the highest-urgency patient ($O(N)$)—create unacceptable algorithmic latency under mass-casualty intake.

This project solves both problems:
1. **Algorithmic Efficiency:** Implements an in-memory **Indexed Min-Heap** with a position hash map that achieves $O(\log N)$ patient insertions, $O(\log N)$ extractions, and $O(\log N)$ priority re-triaging, alongside a linked-list **FIFO Queue** for fair physician allocation and **Singly Linked Lists** for immutable patient treatment timelines.
2. **Clinical Reliability:** Couples custom in-memory data structures with transactional **MySQL** database persistence, ensuring zero patient loss upon system restarts while eliminating queue starvation via an automated **Aging Boost** algorithm.



