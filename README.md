# KritAI

## Inspiration
What began as an attempt to bring Git to the world of digital art evolved into something bigger: an AI-powered co-creator embedded right inside your canvas.

As artists and programmers, we often wondered—what if creative workflows had the same tooling as software development?
- What if you could **branch** your art to explore different styles without duplicating files or layers?
- What if you could **commit versions** of your work with thumbnails, timestamps, and layer states?
- What if you had an **AI art copilot** that could improve your sketches directly on the canvas, guided by prompts and layer data?
- What if you could receive **spontaneous art critique** using AI?

With Krita's Python plugins, we managed to bridge this gap, bringing common developer tools to an artist's world. 

## What it does
kritAI is a Krita plugin that fuses version control and AI assistance into your digital art workflow. It ships with two main components:

#### 🎨 kritAI: AI art generation
Choose from the following image generation modes to create/modify the layer that is generated on the canvas. 

* **Generate** – Create a new image layer from a prompt.
* **Vary** – Generate image variations based on the current canvas.
* **Edit** – Paint a mask and prompt the AI to fill that region using selected layers for context.

#### 🌳 ArtGit: Git for Art
* **Committing** – Save your current canvas and its layer structure with a commit message.
* **Branching** – Create branches to explore alternate versions or styles.
* **Preview Version History** – Visual tree view of all commits with thumbnails, timestamps, and messages.
* **Server Upload** – Upload your art, view art created by other users, and commit tree to the cloud!

## How we built it
- Python to develop Krita plugins
- PyQt for UI/UX design of the dockers 
- OpenAI API (DALL-E) to retrieve the AI-generated image based on layer information and prompt
- Next.js for image hosting and MongoDB for image data storing 

## Challenges we ran into
- AI image generation accuracy
- Learning new skills (ex. PyQt)
- Visualizing branch history to users through a graph 

## Accomplishments that we're proud of
- AI image generation saved as a layer directly on the canvas
- Building a plugin that we would use IRL :)
- Visualizing branch history to users through a graph!!!

## What's next for kritAI
- Uploading commit history alongside Krita files to DB so others can "clone" both the `.kra` file and its commits + branches

## Slides
https://www.figma.com/proto/jco5lfVMJ4WJqM8iOLsyWr/SpurHacks2025?node-id=1-575&page-id=0%3A1&scaling=fit
