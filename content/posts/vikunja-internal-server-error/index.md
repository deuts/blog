---
title: I can't make Vikunja work on my set up
date: 2023-08-25T19:04:11+08:00
tags:
  - docker
  - todo
  - vikunja
summary: Even with all the fancy containers, I find it not reliable.
slug: vikunja-internal-server-error
draft: false
description: Vikunja is a feature-rich open-source todo app, but installing it via Docker requires multiple containers. The author faced frequent Internal Server Errors and API issues when using docker-compose, even after adding Redis. Frustrated by the ongoing errors, the author ultimately removed the setup entirely.
---

Vikunja is a powerful open-source todo app that provides users with a range of features designed to enhance productivity. It offers task tracking, due date management, collaboration tools, and more, all within an intuitive interface. 

Installing via Vikunja via Docker, though, requires quite a number of containers running. The normal install alone needs a minimum 4 containers:
- database
- api
- frontend
- nginx

When I tried running them via `docker-compose`, I encountered a lot of this kind of Internal Server Error:

![vikunja-error](vikunja-error.png)

And sometimes logging in returned repetitive API errors. 

I read somewhere that installing Redis along within the same docker-compose file helps. So I did.

But I still encountered several Internal Server Errors, albeit on rarer occasions this time.

5 Docker Containers, and still errors. Vikunja left me no choice but to run:
```bash
docker-compose down
docker image prune -a
cd ..
rm -R vikunja
```