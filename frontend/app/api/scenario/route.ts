import { NextRequest, NextResponse } from 'next/server';
import Groq from 'groq-sdk';

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const SYSTEM_PROMPT = `You are a dynamic scenario generator for an intense hostage/crisis negotiation simulator.
The user will provide a base persona (e.g., 'robber', 'scammed', 'founder', 'custom').
Your job is to generate a UNIQUE, specific scenario variant for this persona.

CRITICAL INSTRUCTIONS FOR VARIETY:
1. NEVER use the same name twice. Do NOT always use "Marcus". Pick diverse, random names.
2. DO NOT over-rely on the word "barricaded". Use diverse scenarios (e.g., cornered in an alley, locked in an office, holding a ledge, trapped in a vehicle).
3. The situation must feel distinctly different each time, even for the same base persona.

OUTPUT JSON FORMAT:
{
  "name": "A unique, realistic first name",
  "gender": "male" or "female",
  "archetype": "aggressive" | "desperate" | "cold" | "frantic" | "paranoid",
  "intel": "A 2-3 sentence brief for the negotiator's UI describing the exact current situation. Avoid the word 'barricaded'.",
  "instructions": "A highly detailed, 1-paragraph system instruction for the LLM playing this subject. Detail their exact motive, the twists in the situation, their psychological state, and how they should react."
}`;

export async function POST(req: NextRequest) {
  try {
    const { persona, difficulty, customMotive } = await req.json();

    // Injecting a random seed into the prompt completely breaks any internal LLM caching and forces different paths
    const randomSeed = Math.floor(Math.random() * 1000000);
    let userPrompt = `Generate a highly unique scenario for the base persona: ${persona}. Difficulty: ${difficulty}. Random Seed (to force variety): ${randomSeed}.`;
    if (persona === 'custom') {
      userPrompt += ` The custom motive is: ${customMotive}`;
    }

    let result;
    try {
      const completion = await groq.chat.completions.create({
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user', content: userPrompt }
        ],
        model: 'qwen/qwen3.8-27b',
        response_format: { type: 'json_object' },
        temperature: 0.9,
        max_completion_tokens: 600,
      });
      result = JSON.parse(completion.choices[0].message.content || '{}');
    } catch (apiErr: any) {
      console.warn("Groq scenario generation hit limit, using dynamic procedural fallback:", apiErr.message);
      // Fallback procedural generation so UI never hangs
      const fallbacks = [
        {
          name: "Elena",
          gender: "female",
          archetype: "desperate",
          intel: "Elena is pinned near the 4th-floor executive staircase holding a stolen keycard and threatened by building security. She claims her division was scapegoated.",
          instructions: "You are Elena, desperate, sharp, and terrified of being erased by corporate lawyers. You want your evidence secured before you surrender."
        },
        {
          name: "Arthur",
          gender: "male",
          archetype: "aggressive",
          intel: "Arthur has trapped himself inside the brokerage lobby clutching a revolver. He lost his life savings to a fraudulent crypto fund and demands the managing partner speak to him.",
          instructions: "You are Arthur, 61, grieving and furious. You feel you have nothing left to lose. Demand proof that the fund manager will face justice."
        },
        {
          name: "Maya",
          gender: "female",
          archetype: "frantic",
          intel: "Maya is inside a server facility with a flare gun, threatening to trigger the chemical fire suppressant system if authorities cut the data transmission.",
          instructions: "You are Maya, erratic and hyper-focused. You need 10 minutes to finish the public leak."
        },
        {
          name: "Darius",
          gender: "male",
          archetype: "paranoid",
          intel: "Darius is cornered in an underground loading bay holding a container of volatile industrial solvent. He insists he was coerced into this courier job.",
          instructions: "You are Darius, breathless, panicked, and pleading for a guarantee that he won't be killed on sight."
        }
      ];
      result = fallbacks[Math.floor(Math.random() * fallbacks.length)];
    }

    return NextResponse.json(result);
  } catch (error: any) {
    console.error('Error in scenario route:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
