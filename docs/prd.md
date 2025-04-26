Thank you for the clarification. Based on your updated directive, I’ve revised the **Product Requirements Document (PRD)** structure to reflect the full scope of the **“Medellín Real Estate CMS & Marketing System”**, where:

- The **CMS is only one component**
    
- The **primary goal is generating qualified renter leads and converting them to bookings**
    
- The stack includes **marketing funnels, WhatsApp flows, Airtable CRM, Claude/Cursor automation, and Webflow UI**
    

---

### 📘 NEW: Full PRD Structure — _Medellín Real Estate CMS & Marketing System_

> **Scope**: A unified marketing + CMS + automation platform for attracting, qualifying, and converting long-term rental leads in Medellín. Powered by AI-first workflows, omnichannel lead generation, and real estate CRM logic.

---

## 📑 Table of Contents

1. **Project Overview**
    
2. **Goals and KPIs**
    
3. **User Personas & Journeys**
    
4. **System Architecture (CMS + CRM + Automations)**
    
5. **Core Modules & Features**
    
6. **Marketing Stack & Funnel Strategy**
    
7. **Airtable CRM Design + Lead Scoring**
    
8. **WhatsApp Automation + Booking Flows**
    
9. **Webflow CMS & Page Types**
    
10. **AI-Powered Content & Workflows (Claude, Cursor, Clay)**
    
11. **User Stories**
    
12. **MVP Feature Scope**
    
13. **Future Enhancements**
    
14. **Glossary**
    

---

## 1. 🔍 Project Overview

**Name:** Medellín Real Estate CMS & Marketing System  
**Type:** Full-stack AI-powered rental marketing & management platform  
**Users:** Real estate marketers, agents, admins, renters  
**Goal:** Automate lead generation, qualification, and bookings through AI + CRM integration

---

## 2. 🎯 Goals and KPIs

|Objective|KPI|
|---|---|
|Generate qualified rental leads|100+ per month from social & search|
|Convert leads to viewings|25% tour booking rate via WhatsApp|
|Automate CRM + follow-up|80% of form/chat leads entered without manual input|
|Reduce time to publish listings|90% of listings AI-generated and posted via Claude|
|Drive traffic to landing pages|30% CTR from paid media to CMS or WhatsApp|

---

## 3. 👥 User Personas & Journeys

|Persona|Goals|Journey|
|---|---|---|
|Renter|Find apartment|Instagram Ad → WhatsApp Chat → Tour Booking|
|Agent|List + Manage properties|Dashboard → Claude Listing Prompt → Webflow Publish|
|Admin|Manage CRM + Ads|Airtable Lead View → Campaign Setup → Retargeting|

See: [3-user-flows-medellin-rentals.md]

---

## 4. 🧱 System Architecture

**Core Stack:**

- **Frontend**: Webflow + GSAP + Swiper.js
    
- **CRM**: Airtable (Properties, Leads, Agents, Status, Score)
    
- **AI Agents**: Claude (blog, listings), Cursor (UX), Clay (lead enrichment)
    
- **Automation**: n8n or Make for WhatsApp, triggers, reminders
    
- **Backend**: Xano (tour booking, lease handling, notifications)
    

See Mermaid `C4Context`, `journey`, and `flowchart` in user flows

---

## 5. 🧩 Core Modules & Features

|Module|Description|
|---|---|
|CMS|Blog, Properties, Agents, Locations|
|Lead Inbox|Airtable base with forms, WhatsApp sync|
|WhatsApp AI Bot|Bookings, tour reminders, FAQ replies|
|Claude Content Agent|Prompts for listings, blogs, captions|
|AI-Powered CRM|Scoring + personalized follow-up|
|Landing Pages|Localized, SEO-driven pages (e.g. /poblado-apartments)|

---

## 6. 📣 Marketing Stack & Funnel Strategy

Sourced from [Advanced Digital Marketing Strategies]:

### Channels:

- Facebook/Instagram Ads → WhatsApp funnel
    
- Google SEO → Blog content → CTA to view properties
    
- Retargeting via Meta Pixel
    

### Tactics:

- Reels + AI captions with Claude
    
- Lead capture quizzes built in Webflow
    
- Auto-publishing property matches via Claude
    

|Funnel Stage|Tools|
|---|---|
|Ad Discovery|Meta Ads, Claude captions|
|Lead Entry|WhatsApp API, Webflow forms|
|Qualification|Clay, n8n|
|Booking|Calendly, WhatsApp|
|Tour Follow-up|Claude + Airtable status|
|Contract & Move-in|Xano, Claude templates|

---

## 7. 📋 Airtable CRM Design

See: [airtable-base.md]

|Table|Key Fields|
|---|---|
|Leads|Name, Phone, WhatsApp Opt-in, Lead Score|
|Properties|Linked to Category, Type, Location|
|Agents|Availability, WhatsApp ID|
|Booking Status|Toured, Contract Sent, Rented|

Features:

- Lead scoring (Clay + Xano)
    
- Booking trigger (Xano)
    
- Auto-updates from Webflow via MCP
    

---

## 8. 💬 WhatsApp Automation

See: [user flows + WhatsApp rental flow.md]

|Flow|Tools|
|---|---|
|New Lead Welcome|WhatsApp → n8n → Airtable|
|Tour Booking|Claude → WhatsApp template|
|Follow-up Reminder|Xano → Claude → WhatsApp|
|Contract Link|Claude → WhatsApp + PDF|
|Move-in Pack|Xano → Claude → WhatsApp|

---

## 9. 🖥️ Webflow CMS + Pages

See: [1-cms.md] + [2-pages.md]

- **CMS Collections**: Properties, Locations, Agents, Blog, Categories, Types
    
- **Dynamic Pages**: Property Detail, Blog Post, Category Filters
    
- **UI Notes**:
    
    - Use sticky filters (Cursor)
        
    - Hero animation (Cursor + GSAP)
        
    - CTA buttons for WhatsApp/Book Tour
        
    - Pages: `/properties`, `/agents`, `/blog`, `/submit-property`
        

---

## 10. 🧠 AI Workflows (Claude + Cursor + Clay)

|Use Case|Prompt/Automation|
|---|---|
|Listing creation|“Generate a property listing with luxury tone, 150 words, in Poblado”|
|WhatsApp reply|“Respond in bilingual tone about parking and pet policy”|
|Blog generator|“Top 10 Medellín Neighborhoods for Remote Workers”|
|Lead scoring|Clay enrich → Airtable score → n8n booking trigger|
|Animation|Cursor prompt: “Create scroll-triggered filter UI using Webflow CMS data”|

See: [custom-gpts.md] + [Repomix Webflow AI Guide]

---

## 11. 🧑‍🤝‍🧑 User Stories

### 🎯 Renter

- "As a renter, I want to view listings and book a tour via WhatsApp in <2 minutes."
    

### 🏡 Agent

- "As an agent, I want to use Claude to write my listings and send contracts without coding."
    

### 👩 Admin

- "As a marketing admin, I want to score leads in Airtable and send targeted WhatsApp blasts."
    

---

## 12. 🚀 MVP Scope

### Must-Have for V1

- Webflow CMS with Properties, Locations, Blog
    
- Airtable base for Leads, Agents
    
- WhatsApp AI Flow: Ad → Tour → CRM
    
- Claude Prompt: Listing writer
    
- Landing Pages: `/poblado-apartments`, `/laureles-homes`
    

---

## 13. 🌱 Future Enhancements

- AI price recommender (Claude + Xano)
    
- Real-time availability sync (Airbnb, NomadList)
    
- Smart lead routing (agent matching)
    
- Landlord dashboard with WhatsApp integration
    
- Facebook Marketplace + Instagram DM bots
    

---

## 14. 📚 Glossary

|Term|Definition|
|---|---|
|**MCP**|Model Context Protocol – syncs AI with Webflow/Airtable|
|**CRM**|Customer Relationship Management – leads, status, follow-up|
|**Claude**|AI agent for content, messages, contract drafts|
|**Cursor AI**|AI for animations, UI logic, CMS editing|
|**Clay**|Enrichment tool – adds data to leads from public web|
|**n8n**|Automation engine for WhatsApp + Claude flows|
|**Xano**|Backend API – bookings, contracts, database|
|**CTA**|Call to Action – button, link, or form to convert traffic|

---

## ✅ Ready to Proceed?

Would you like:

- Claude prompt templates for WhatsApp, listings, blog posts?
    
- Mermaid diagram of system architecture or WhatsApp flows?
    
- MVP go-live checklist?
    

I'm ready when you are.