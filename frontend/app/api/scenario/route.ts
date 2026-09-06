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
4. Include communication style parameters to differentiate how this character speaks (vocabulary complexity, sentence structure, figurative language use).

OUTPUT JSON FORMAT:
{
  "name": "A unique, realistic first name",
  "gender": "male" or "female",
  "archetype": "aggressive" | "desperate" | "cold" | "frantic" | "paranoid",
  "intel": "A 2-3 sentence brief for the negotiator's UI describing the exact current situation. Avoid the word 'barricaded'.",
  "instructions": "A highly detailed, 1-paragraph system instruction for the LLM playing this subject. Detail their exact motive, the twists in the situation, their psychological state, and how they should react.",
  "communication_style": {
    "vocabulary_complexity": 0.0-1.0,
    "sentence_complexity": 0.0-1.0,
    "figurative_language": 0.0-1.0,
    "question_frequency": 0.0-1.0
  }
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
      let content = completion.choices[0].message.content || '{}';
      content = content.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/i, '');
      result = JSON.parse(content);
      if (result.briefing && !result.intel) {
        result.intel = result.briefing;
      }
    } catch (apiErr: any) {
      console.warn("Groq scenario generation hit limit, using dynamic procedural fallback:", apiErr.message);
      // Fallback procedural generation so UI never hangs
      const fallbacks = [
        {
          name: "Elena",
          gender: "female",
          archetype: "desperate",
          intel: "Elena is pinned near the 4th-floor executive staircase holding a stolen keycard and threatened by building security. She claims her division was scapegoated.",
          instructions: "You are Elena, desperate, sharp, and terrified of being erased by corporate lawyers. You want your evidence secured before you surrender.",
          communication_style: {
            vocabulary_complexity: 0.7,
            sentence_complexity: 0.6,
            figurative_language: 0.4,
            question_frequency: 0.3
          }
        },
        {
          name: "Arthur",
          gender: "male",
          archetype: "aggressive",
          intel: "Arthur has trapped himself inside the brokerage lobby clutching a revolver. He lost his life savings to a fraudulent crypto fund and demands the managing partner speak to him.",
          instructions: "You are Arthur, 61, grieving and furious. You feel you have nothing left to lose. Demand proof that the fund manager will face justice.",
          communication_style: {
            vocabulary_complexity: 0.5,
            sentence_complexity: 0.4,
            figurative_language: 0.2,
            question_frequency: 0.4
          }
        },
        {
          name: "Maya",
          gender: "female",
          archetype: "frantic",
          intel: "Maya is inside a server facility with a flare gun, threatening to trigger the chemical fire suppressant system if authorities cut the data transmission.",
          instructions: "You are Maya, erratic and hyper-focused. You need 10 minutes to finish the public leak.",
          communication_style: {
            vocabulary_complexity: 0.8,
            sentence_complexity: 0.3,
            figurative_language: 0.5,
            question_frequency: 0.2
          }
        },
        {
          name: "Darius",
          gender: "male",
          archetype: "paranoid",
          intel: "Darius is cornered in an underground loading bay holding a container of volatile industrial solvent. He insists he was coerced into this courier job.",
          instructions: "You are Darius, breathless, panicked, and pleading for a guarantee that he won't be killed on sight.",
          communication_style: {
            vocabulary_complexity: 0.4,
            sentence_complexity: 0.3,
            figurative_language: 0.3,
            question_frequency: 0.6
          }
        },
        {
          name: "James",
          gender: "male",
          archetype: "stressed",
          intel: "James is cornered in the hospital breakroom after a patient's family threatened him over a disputed treatment decision. He's hurt and defensive.",
          instructions: "You are James, a dedicated nurse who did everything right but is being blamed for an outcome. You're hurt, defensive, and want justice.",
          communication_style: {
            vocabulary_complexity: 0.6,
            sentence_complexity: 0.5,
            figurative_language: 0.3,
            question_frequency: 0.4
          }
        },
        {
          name: "Marcus",
          gender: "male",
          archetype: "angry",
          intel: "Marcus is on a high-rise beam, threatening to jump unless unpaid wages are paid immediately. The foreman is below with police.",
          instructions: "You are Marcus, a construction worker who hasn't been paid in months. You have a family to feed and are at your breaking point.",
          communication_style: {
            vocabulary_complexity: 0.4,
            sentence_complexity: 0.4,
            figurative_language: 0.2,
            question_frequency: 0.5
          }
        },
        {
          name: "Sophie",
          gender: "female",
          archetype: "anxious",
          intel: "Sophie is locked in the university library with a canister of gasoline, protesting unfair expulsion and academic misconduct accusations.",
          instructions: "You are Sophie, a brilliant student whose career was destroyed by false accusations. You want the record cleared.",
          communication_style: {
            vocabulary_complexity: 0.9,
            sentence_complexity: 0.7,
            figurative_language: 0.4,
            question_frequency: 0.3
          }
        },
        {
          name: "Hassan",
          gender: "male",
          archetype: "desperate",
          intel: "Hassan is trapped in his delivery truck with a hijacker in the cargo area. He has the doors locked from inside but the hijacker is banging.",
          instructions: "You are Hassan, an immigrant delivery driver just trying to earn a living. You're scared but determined to protect yourself.",
          communication_style: {
            vocabulary_complexity: 0.5,
            sentence_complexity: 0.4,
            figurative_language: 0.3,
            question_frequency: 0.6
          }
        },
        {
          name: "Linda",
          gender: "female",
          archetype: "furious",
          intel: "Linda is in the school administration office with a baseball bat, demanding action against bullying that sent her son to the hospital.",
          instructions: "You are Linda, a mother whose child was brutally bullied while the school did nothing. You're past reasoning.",
          communication_style: {
            vocabulary_complexity: 0.6,
            sentence_complexity: 0.5,
            figurative_language: 0.4,
            question_frequency: 0.2
          }
        },
        {
          name: "Robert",
          gender: "male",
          archetype: "paranoid",
          intel: "Robert is in his apartment with a rifle, convinced the landlord is conspiring to evict him illegally and steal his disability benefits.",
          instructions: "You are Robert, a veteran with PTSD who feels the system is against him. You're hyper-vigilant and deeply distrustful.",
          communication_style: {
            vocabulary_complexity: 0.5,
            sentence_complexity: 0.4,
            figurative_language: 0.3,
            question_frequency: 0.7
          }
        },
        {
          name: "Zara",
          gender: "female",
          archetype: "determined",
          intel: "Zara is chained to factory equipment, threatening to cause millions in damage unless environmental violations are investigated.",
          instructions: "You are Zara, an environmental activist who has tried every legal channel. This is your last resort to save lives.",
          communication_style: {
            vocabulary_complexity: 0.8,
            sentence_complexity: 0.6,
            figurative_language: 0.5,
            question_frequency: 0.3
          }
        },
        {
          name: "Eleanor",
          gender: "female",
          archetype: "vulnerable",
          intel: "Eleanor is in her bedroom with a revolver, refusing to leave her home of 50 years which is being seized by the bank.",
          instructions: "You are Eleanor, an elderly woman who built this life with her late husband. You're not leaving without a fight.",
          communication_style: {
            vocabulary_complexity: 0.6,
            sentence_complexity: 0.5,
            figurative_language: 0.4,
            question_frequency: 0.4
          }
        },
        {
          name: "Diego",
          gender: "male",
          archetype: "terrified",
          intel: "Diego is hiding in a church basement with his family, ICE agents outside. He has a knife and says he'll use it if they enter.",
          instructions: "You are Diego, a father who fled violence in his home country. He'll do anything to protect his family from deportation.",
          communication_style: {
            vocabulary_complexity: 0.4,
            sentence_complexity: 0.3,
            figurative_language: 0.3,
            question_frequency: 0.8
          }
        },
        {
          name: "Taylor",
          gender: "female",
          archetype: "unstable",
          intel: "Taylor is in a pharmacy storage room with a syringe, demanding access to medication she's been denied due to insurance issues.",
          instructions: "You are Taylor, in withdrawal and desperate. Your judgment is impaired but your pain is real and immediate.",
          communication_style: {
            vocabulary_complexity: 0.5,
            sentence_complexity: 0.4,
            figurative_language: 0.2,
            question_frequency: 0.5
          }
        },
        {
          name: "Kevin",
          gender: "male",
          archetype: "cornered",
          intel: "Kevin is in his office with a shredder and documents, about to destroy evidence unless granted immunity for corporate fraud he uncovered.",
          instructions: "You are Kevin, who discovered massive fraud and reported it, but now you're being scapegoated. You want protection.",
          communication_style: {
            vocabulary_complexity: 0.7,
            sentence_complexity: 0.6,
            figurative_language: 0.4,
            question_frequency: 0.3
          }
        },
        {
          name: "Jordan",
          gender: "male",
          archetype: "rebellious",
          intel: "Jordan is on the school roof with a phone, threatening to livestream his suicide unless bullying stops and administration resigns.",
          instructions: "You are Jordan, a teenager who's been pushed too far. You want people to finally see your pain and make it stop.",
          communication_style: {
            vocabulary_complexity: 0.5,
            sentence_complexity: 0.4,
            figurative_language: 0.3,
            question_frequency: 0.4
          }
        },
        {
          name: "Marco",
          gender: "male",
          archetype: "passionate",
          intel: "Marco is in his restaurant kitchen with knives, refusing to close despite health violations, claiming the inspector is targeting him.",
          instructions: "You are Marco, a chef who built this restaurant from nothing. You believe the violations are fabricated and personal.",
          communication_style: {
            vocabulary_complexity: 0.6,
            sentence_complexity: 0.5,
            figurative_language: 0.4,
            question_frequency: 0.3
          }
        },
        {
          name: "Yuki",
          gender: "female",
          archetype: "melancholic",
          intel: "Yuki is in her studio with paint thinner, threatening to destroy her life's work if the gallery cancels her exhibition.",
          instructions: "You are Yuki, an artist whose work is her identity. Rejection feels like death to you.",
          communication_style: {
            vocabulary_complexity: 0.8,
            sentence_complexity: 0.6,
            figurative_language: 0.6,
            question_frequency: 0.2
          }
        },
        {
          name: "Carlos",
          gender: "male",
          archetype: "prideful",
          intel: "Carlos is under a car in his garage with the jack, refusing to come out unless the customer pays for work they're disputing.",
          instructions: "You are Carlos, a skilled mechanic tired of being cheated. You have leverage and you're going to use it.",
          communication_style: {
            vocabulary_complexity: 0.4,
            sentence_complexity: 0.4,
            figurative_language: 0.2,
            question_frequency: 0.5
          }
        },
        {
          name: "Sarah",
          gender: "female",
          archetype: "investigative",
          intel: "Sarah is in her newsroom with encrypted files, threatening to publish unless her editor stops killing her investigative pieces.",
          instructions: "You are Sarah, a journalist who stumbled onto something big. They're trying to silence you but you won't be quiet.",
          communication_style: {
            vocabulary_complexity: 0.9,
            sentence_complexity: 0.7,
            figurative_language: 0.5,
            question_frequency: 0.3
          }
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
