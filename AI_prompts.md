# AI Prompts

## Setup

**Prompt:**
> Today we'll be working in @Homeworks/4 on a website with a chatbot for Campus Customs. We'll be building a react+vite typescript front end and a python fast API backend.  unzip @Homeworks/4/data.zip

## P1 - Vibe coder prompts

**Prompt:**
> P1 - Vibe coder prompts: Create AI_prompts.md and record the prompts I send you in this chat for each problem. Include a follow-up only if I used one, with a sentence explaining what was missing from the first result.

## P2 - Analyze the database

**Prompt:**
> P2 - Analyze the database.  Can you examine the Campus Customs SQLite database and help me understand how the data is organized? I'm  interested in the product catalogue, inventory, and user information. Create output/harness.md documenting the tables, their fields, and how we'll use that information for the storefront and chatbot. This is super important bc We'll base everything on the actual database.

**Follow-up:**
> Sorry, I meant this is super important bc We'll keep expanding  after on this harness file

The first result was written as a one-time snapshot of the database, with no structure for growing it in later problems (no contents list, open-questions list, or changelog).

## P3 — Build the Website

**Prompt:**
> Let's build a Campus Customs online store using the React, Vite, and TypeScript setup from our web applications lecture. I want Home, Products, About Us, Login, and Create Account pages, with a navigation bar connecting them. Use the SQLite database to display the products with their images, prices, and descriptions, and make each product clickable so customers can see its full details. Use the Campus Customs website as inspiration for the Home and About pages, but write original content. Also include a chatbot window in the bottom-right corner that we'll connect to an agent later. Keep the frontend and backend organized separately.

## P4 - Registration and login

**Prompt:**
> P4 - registration and login: Let's create a fucntional login so users can register with their first name, last name, email, and password, and then log in to their accounts. Help me connect this to the users table in the SQLite database, hash the passwords.  Update harness.md to explain how the authentication works by adding a few unique codes to the passcode .

## P5 — PydanticAI Agent Backend

**Prompt:**
> P5 — PydanticAI Agent Backend 
> I want to connect the chatbot to a working AI agent using PydanticAI and FastAPI. Keep main.py as the FastAPI entry point and separate the agent configuration, tools, Pydantic models, and system prompt into their own files. Use Portkey and the  model configuration from my lecture folders, with the API key stored in .env. Give the chatbot the personality of a helpful customer service person at Campus Customs  and connect it to the existing chat interface. Update harness.md to explain how the frontend communicates with the agent.

## P6 — Product and Inventory Tools

**Prompt:**
> P6 — Product and Inventory Tools  give the agent tools to look up product information directly from our SQLite database. It should be able to answer questions about product descriptions, prices, and stock levels, including available sizes. Define the tools in `tools.py` with appropriate structured outputs in `models.py`, and update the system prompt so the agent knows when to call them. I want its answers to reflect actual database information, especially when something is out of stock. Document how the tools work in `harness.md`.

## P7 — Chat Search That Updates the Page

**Prompt:**
> P7 — Chat Search That Updates the Page; 
> I want customers to be able to search for products through the chatbot and see the results directly on the website. For example, if someone asks what hoodies are available, the agent should search the database and return matching products as structured data. The frontend should then display these products as cards with images, prices, and descriptions. Make sure the cards link to the individual product pages we built earlier. Update the agent prompt and harness.md to explain how the search results are passed from the backend to the frontend.

## P8 — Customer Memory

**Prompt:**
> P8 — Customer Memory: Now I want the chatbot to remember customers across sessions. When someone is logged in, save their conversation history in the SQLite database and reload it when they return. Pass their name and email to the agent through PydanticAI dependencies or a similar approach. I also want the chatbot to know which product page a customer is viewing, so it can understand questions like "Is this available in pink?" without needing the product name repeated. Guests should still be able to chat without saving their history. Document the memory and context setup in `harness.md`.

## P9 — Usability Improvements

**Prompt:**
> P9 — Usability Improvements: For the frontend, add product filters by category and size to make it easier for a shopper to filter through the catalogue. also make the background for each merch more fitted to the color of the merch (e.g. black merch, white bkgd and vice versa) to make it look more polished. For the chatbot on the backend, add recommendations for similar products when something is unavailable to improve the customer experience as well as likelihood that the person will purchase something from CC. also  have it ask clarifying questions when a customer makes a vague request rather than guessing, to make sure it gets the customer the right thing.  create output/usability.md explaining my above reasoning for adding each (two frontend and two backend) improvement

## P10 — Style the Website

**Prompt:**
> P10 — Style the Website: To make the website feels like a real Campus Customs store, use a modern Yale-inspired design with navy blue, white, clean typography, and good spacing. Make the homepage more engaging, improve how products are presented, and make the chatbot feel like part of the website. make the chatbot a cutout picture of handsome dan. Keep the functionality we've already built. Create `output/design.md` explaining how the changes i made make it look like its truly Yale invokes Yale pride and also shows that the shop is fully supported by yale, and not a knock off brand selling merch at discounted price.

**Additional prompt (sent during P10):**
> Can you help me create output/app_check.html where i can document the results?

## P11 — Site Testing

**Prompt:**
> P11 — Site Testing add these to the output/app_check.html Under each corresponding screenshots, include the following explanations: 1. matching product cards after a chatbot search 2. showing inventory stock levels 3. a usability improvement ive added being able to filter and then sort by size

## P12 — Audit Trail and Safety

**Prompt:**
> P12 — Audit Trail and Safety: I want to make the agent's behavior easier to track and more secure. Add an audit trail in output/audit_trail.json that records agent activity, including timestamps, tools called, short inputs and results, and why the agent stopped. Make sure new records are appended rather than replacing previous ones. Also update the system prompt with safety rules to protect customer information and wellbeing, prevent invented product claims, and handle attempts to manipulate the agent. Finally, complete harness.md with the models, tools, security rules, agent limits, and instructions for running the application.

## P13 — GitHub Submission

**Prompt:**
> P13 — GitHub Submission - Can you help me prepare this project for GitHub? Make sure the required files are organized inside the `hw4` folder, create a README with instructions for running the frontend and backend, and check that all the dependencies are listed. Set up `.gitignore` so the database, product images, API keys, and other sensitive files aren't committed. Include an `.env.example` with placeholder values. Please review the folder structure and identify anything missing before I push the project.

**Additional prompt (sent during P13):**
> create a repo, you have access to my github
