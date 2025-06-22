## Inspiration
What initially started as a Git agent for digital art has blossomed into an AI agent that converts your sketches into a masterpiece directly onto your canvas (+ the initial Git agent). 

As artists and programmers, we've wondered if we could integrate various programming services into our art program, such as...
- Maintaining multiple **branches** to test different rendering styles.
- Return to various **commits**, retrieving its layer data to the canvas.
- Receiving spontaneous art critique using **AI**.
- Copilot for art that will draw over + improve specific areas on the canvas based on layer information and prompts.

With Krita's Python plugins, we managed to bridge this gap, bringing common developer tools to an artist's world. 


## What it does
kritAI is a Krita plugin that includes two tools directly into the program's UI: Git for art and AI image generation.

#### kritAI:
Choose from the following image generation modes to create/modify the layer that is generated on the canvas. 
* **Generate:** Adds a new layer onto your canvas that satisfies your prompt.
* **Vary:** Changes canvas with image-to-image generation that satisfies your prompt. 
* **Edit:** Select a region for the AI image generator to fill, referring to user-specified layer data and a prompt as context.

#### ArtGit:
* **Committing:** With a commit message, save the current canvas with its layer information locally.
* **Branches:** Stick with `main` or create a new branch to store commits.
* **Preview Version History:** Version history of the currently selected branch will show a thumbnail of the commit, the commit message, and the time of the commit. 
* **Upload to Server:** Upload/view art built with this plugin!

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