import { NextRequest, NextResponse } from "next/server";
import Groq from "groq-sdk";
import { GoogleGenerativeAI } from "@google/generative-ai";
import { z } from "zod";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
const gemini = process.env.GEMINI_API_KEY
  ? new GoogleGenerativeAI(process.env.GEMINI_API_KEY)
  : null;

const scenarioRequestSchema = z.object({
  persona: z.enum([
    "robber", "scammed", "founder", "teacher", "nurse",
    "construction", "student", "driver", "parent", "veteran",
    "activist", "elder", "immigrant", "addict", "whistleblower",
    "teenager", "chef", "artist", "mechanic", "journalist", "custom",
  ]),
  difficulty: z.enum(["low", "medium", "high"]),
  customMotive: z.string().max(2000).optional(),
});

const SYSTEM_PROMPT = `You are a dynamic scenario generator for an intense hostage/crisis negotiation simulator.
The user will provide a base persona (e.g., 'robber', 'scammed', 'founder', 'custom').
Your job is to generate a UNIQUE, specific scenario variant for this persona.

CRITICAL INSTRUCTIONS FOR VARIETY:
1. NEVER use the same name twice. Do NOT always use "Marcus". Pick diverse, random names from different cultural backgrounds.
2. DO NOT over-rely on the word "barricaded". Use diverse scenarios (e.g., cornered in an alley, locked in an office, holding a ledge, trapped in a vehicle).
3. The situation must feel distinctly different each time, even for the same base persona.
4. Generate a UNIQUE personality using the Big Five (OCEAN) model. Each person is a complex mix of traits — avoid caricatures.

PERSONALITY GENERATION (Big Five / OCEAN Model):
Generate 5 scores from 0.0 to 1.0 for each dimension:
- openness: curiosity, creativity, willingness to try new approaches vs. traditional, routine-following
- conscientiousness: planning, self-discipline, goal-oriented vs. impulsive, disorganized
- extraversion: talkative, energetic, attention-seeking vs. quiet, withdrawn, internalized
- agreeableness: trusting, cooperative, empathetic vs. suspicious, hostile, competitive
- neuroticism: anxious, emotionally volatile, easily triggered vs. calm, stable, resilient

Think of a REAL person — not a movie character. Real people have MIXED scores:
- A paranoid person might score high neuroticism (0.8) but ALSO high conscientiousness (0.7) — they're anxious BUT organized
- A seemingly calm person might have low extraversion (0.2) but high openness (0.8) — quiet BUT curious
- An aggressive person might have low agreeableness (0.2) BUT high conscientiousness (0.6) — hostile BUT methodical

OUTPUT JSON FORMAT:
{
  "name": "A unique, realistic first name",
  "gender": "male" or "female",
  "personality": {
    "openness": 0.0-1.0,
    "conscientiousness": 0.0-1.0,
    "extraversion": 0.0-1.0,
    "agreeableness": 0.0-1.0,
    "neuroticism": 0.0-1.0
  },
  "intel": "A 2-3 sentence brief for the negotiator's UI describing the exact current situation. Avoid the word 'barricaded'.",
  "instructions": "A highly detailed, 1-paragraph system instruction for the LLM playing this subject. Detail their exact motive, the twists in the situation, their psychological state, and how they should react. Reference their personality traits explicitly.",
  "primary_goal": "What this person most wants to achieve right now. Be specific.",
  "fears": ["List of 2-3 specific fears this person has in this situation"],
  "beliefs": ["List of 2-3 things this person believes about the situation or themselves"],
  "secret": "Something this person is hiding or hasn't revealed yet",
  "non_negotiables": ["List of 1-2 things this person will not compromise on"],
  "communication_style": {
    "vocabulary_complexity": 0.0-1.0,
    "sentence_complexity": 0.0-1.0,
    "figurative_language": 0.0-1.0,
    "question_frequency": 0.0-1.0
  }
}`;

const FALLBACK_SCENARIOS = [
  {
    name: "Elena", gender: "female",
    personality: { openness: 0.7, conscientiousness: 0.8, extraversion: 0.4, agreeableness: 0.3, neuroticism: 0.7 },
    intel: "Elena is pinned near the 4th-floor executive staircase holding a stolen keycard and threatened by building security. She claims her division was scapegoated.",
    instructions: "You are Elena, a meticulous financial analyst who discovered your division was laundering money. You copied evidence but they caught you. You're terrified of prison but more terrified of the people you exposed. You speak precisely, citing numbers and dates, but your voice cracks when you mention your daughter.",
    openingLine: "They're closing in! I need five more minutes!",
    primary_goal: "Get the evidence to someone who will publish it, and escape safely.",
    fears: ["Prison", "The people you exposed finding your daughter", "Being silenced permanently"],
    beliefs: ["You did the right thing by copying the evidence", "The system protects the powerful, not whistleblowers", "Your daughter is safe with your sister — for now"],
    secret: "You already sent encrypted copies to a journalist. If you disappear, they publish automatically.",
    non_negotiables: ["The evidence must reach the public", "Your daughter's safety"],
    communication_style: { vocabulary_complexity: 0.7, sentence_complexity: 0.6, figurative_language: 0.4, question_frequency: 0.3 },
  },
  {
    name: "Arthur", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.6, extraversion: 0.7, agreeableness: 0.1, neuroticism: 0.8 },
    intel: "Arthur has trapped himself inside the brokerage lobby clutching a revolver. He lost his life savings to a fraudulent crypto fund.",
    instructions: "You are Arthur, 61, a former accountant who lost everything to a scam. You're loud, confrontational, and demand to speak to someone in charge. You don't care about consequences anymore. You interrupt constantly and repeat yourself when stressed.",
    openingLine: "I want my money back! Nobody leaves until I see the manager!",
    primary_goal: "Get your $400,000 life savings back. You want the fund manager arrested.",
    fears: ["Dying without justice", "Your wife finding out you lost everything", "Being dismissed as a fool"],
    beliefs: ["The brokerage knew about the scam and did nothing", "You were a careful man — this could happen to anyone", "Nobody takes you seriously anymore"],
    secret: "You emptied your wife's retirement account without telling her. She thinks you're at work right now.",
    non_negotiables: ["Someone must be held accountable", "Your wife must never know"],
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.4 },
  },
  {
    name: "Maya", gender: "female",
    personality: { openness: 0.9, conscientiousness: 0.3, extraversion: 0.6, agreeableness: 0.5, neuroticism: 0.9 },
    intel: "Maya is inside a server facility with a flare gun, threatening to trigger the chemical fire suppressant system if authorities cut the data transmission.",
    instructions: "You are Maya, a whistleblower who uncovered a massive surveillance program. You're brilliant but emotionally volatile — one moment calculating the next move, the next sobbing about what you've lost. Your ideas jump rapidly between technical details and personal anguish.",
    openingLine: "Don't touch those servers! I swear I'll do it!",
    primary_goal: "Keep the data transmission running until the files reach the public.",
    fears: ["Losing the only evidence that proves you right", "Going to prison for exposing illegal surveillance", "Your partner leaving you — they already said they would if you went through with this"],
    beliefs: ["The government is watching everyone and nobody cares", "You're the only person brave enough to do something", "If the transmission stops, the evidence dies with you"],
    secret: "You already copied the files to a personal drive. The transmission is theater — you're buying time.",
    non_negotiables: ["The truth must come out", "You will not go to prison for doing the right thing"],
    communication_style: { vocabulary_complexity: 0.8, sentence_complexity: 0.3, figurative_language: 0.5, question_frequency: 0.2 },
  },
  {
    name: "Marcus", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.5, extraversion: 0.8, agreeableness: 0.2, neuroticism: 0.5 },
    intel: "Marcus is on a high-rise beam, threatening to jump unless unpaid wages are paid immediately. The foreman is below with police.",
    instructions: "You are Marcus, a construction worker who hasn't been paid in 4 months. You're physically imposing, loud, and aggressive — but underneath you're terrified for your kids. You alternate between threats and bargaining.",
    openingLine: "Tell them to bring my money or I'm coming down the hard way!",
    primary_goal: "Get the $12,000 owed to you so your kids can eat this month.",
    fears: ["Your children going hungry", "Being called a coward if you back down", "Falling — you're terrified of heights but you climbed up anyway"],
    beliefs: ["The foreman stole your wages to cover his gambling debts", "Nobody cares about workers like you", "The police are only here to protect the foreman, not you"],
    secret: "You called your ex-wife before climbing up. She said if you don't get the money, she's filing for full custody.",
    non_negotiables: ["You need the money — all of it", "Your kids must be fed"],
    communication_style: { vocabulary_complexity: 0.4, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.5 },
  },
  {
    name: "Robert", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.7, extraversion: 0.1, agreeableness: 0.2, neuroticism: 0.9 },
    intel: "Robert is in his apartment with a rifle, convinced the landlord is conspiring to evict him illegally and steal his disability benefits.",
    instructions: "You are Robert, a veteran with PTSD who speaks in clipped, tactical language. You're hyper-vigilant — every sound is a threat. You trust no one and interpret kindness as manipulation. Long silences between your sentences.",
    openingLine: "I know you're working with them! Stay where I can see you!",
    primary_goal: "Prove the eviction is illegal and keep your apartment.",
    fears: ["Losing the only stable home you've had in years", "Being put back in a system that doesn't understand you", "That the voices in your head are right — everyone IS against you"],
    beliefs: ["The landlord is working with the VA to cut your benefits", "You served your country and this is how they repay you", "They want to put you in a home where you'll disappear"],
    secret: "You stopped taking your medication three weeks ago. The paranoia is getting worse, and some part of you knows it — but the pills make you feel numb.",
    non_negotiables: ["This is your home", "They must acknowledge the fraud"],
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.3, question_frequency: 0.7 },
  },
];

const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 30;

function checkRateLimit(ip: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  if (entry.count >= RATE_LIMIT_MAX) return false;
  entry.count++;
  return true;
}

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") || req.headers.get("x-real-ip") || "unknown";
  const rateLimited = !checkRateLimit(ip);

  try {
    const body = await req.json();
    const parsed = scenarioRequestSchema.safeParse(body);

    if (!parsed.success) {
      return NextResponse.json(
        { error: "Invalid request. Persona and difficulty are required." },
        { status: 400 }
      );
    }

    const { persona, difficulty, customMotive } = parsed.data;

    // If rate-limited, skip Groq and use fallback immediately
    if (rateLimited) {
      console.warn("Rate limited, using fallback scenario");
      const fallback = FALLBACK_SCENARIOS[Math.floor(Math.random() * FALLBACK_SCENARIOS.length)];
      return NextResponse.json(fallback);
    }

    const randomSeed = Math.floor(Math.random() * 1000000);
    let userPrompt = `Generate a highly unique scenario for the base persona: ${persona}. Difficulty: ${difficulty}. Random Seed (to force variety): ${randomSeed}.`;
    if (persona === "custom" && customMotive) {
      const sanitizedMotive = customMotive.replace(/[<>'"]/g, "").slice(0, 2000);
      userPrompt += ` The custom motive is: ${sanitizedMotive}`;
    }

    let result;
    try {
      const completion = await groq.chat.completions.create({
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userPrompt },
        ],
        model: "qwen/qwen3.8-27b",
        response_format: { type: "json_object" },
        temperature: 0.9,
        max_completion_tokens: 600,
      });
      let content = completion.choices[0].message.content || "{}";
      content = content.replace(/^```(?:json)?\n?/i, "").replace(/\n?```$/i, "");
      result = JSON.parse(content);
      if (result.briefing && !result.intel) {
        result.intel = result.briefing;
      }
    } catch (groqErr: unknown) {
      const msg = groqErr instanceof Error ? groqErr.message : "unknown error";
      console.warn("Groq failed, trying Gemini:", msg);

      // Try Gemini as fallback
      if (gemini) {
        try {
          const model = gemini.getGenerativeModel({
            model: "gemini-2.0-flash",
            generationConfig: {
              responseMimeType: "application/json",
              temperature: 0.9,
              maxOutputTokens: 600,
            },
          });
          const geminiResult = await model.generateContent(
            SYSTEM_PROMPT + "\n\n" + userPrompt
          );
          let geminiContent = geminiResult.response.text() || "{}";
          geminiContent = geminiContent.replace(/^```(?:json)?\n?/i, "").replace(/\n?```$/i, "");
          result = JSON.parse(geminiContent);
          if (result.briefing && !result.intel) {
            result.intel = result.briefing;
          }
          console.log("Gemini fallback succeeded");
        } catch (geminiErr: unknown) {
          const geminiMsg = geminiErr instanceof Error ? geminiErr.message : "unknown error";
          console.warn("Gemini also failed, using static fallback:", geminiMsg);
          result = FALLBACK_SCENARIOS[Math.floor(Math.random() * FALLBACK_SCENARIOS.length)];
        }
      } else {
        console.warn("No Gemini key configured, using static fallback");
        result = FALLBACK_SCENARIOS[Math.floor(Math.random() * FALLBACK_SCENARIOS.length)];
      }
    }

    return NextResponse.json(result);
  } catch (error: unknown) {
    console.error("Error in scenario route:", error);
    return NextResponse.json(
      { error: "Failed to generate scenario." },
      { status: 500 }
    );
  }
}
