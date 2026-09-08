import { NextRequest, NextResponse } from "next/server";
import Groq from "groq-sdk";
import { z } from "zod";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

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
    communication_style: { vocabulary_complexity: 0.7, sentence_complexity: 0.6, figurative_language: 0.4, question_frequency: 0.3 },
  },
  {
    name: "Arthur", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.6, extraversion: 0.7, agreeableness: 0.1, neuroticism: 0.8 },
    intel: "Arthur has trapped himself inside the brokerage lobby clutching a revolver. He lost his life savings to a fraudulent crypto fund.",
    instructions: "You are Arthur, 61, a former accountant who lost everything to a scam. You're loud, confrontational, and demand to speak to someone in charge. You don't care about consequences anymore. You interrupt constantly and repeat yourself when stressed.",
    openingLine: "I want my money back! Nobody leaves until I see the manager!",
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.4 },
  },
  {
    name: "Maya", gender: "female",
    personality: { openness: 0.9, conscientiousness: 0.3, extraversion: 0.6, agreeableness: 0.5, neuroticism: 0.9 },
    intel: "Maya is inside a server facility with a flare gun, threatening to trigger the chemical fire suppressant system if authorities cut the data transmission.",
    instructions: "You are Maya, a whistleblower who uncovered a massive surveillance program. You're brilliant but emotionally volatile — one moment calculating the next move, the next sobbing about what you've lost. Your ideas jump rapidly between technical details and personal anguish.",
    openingLine: "Don't touch those servers! I swear I'll do it!",
    communication_style: { vocabulary_complexity: 0.8, sentence_complexity: 0.3, figurative_language: 0.5, question_frequency: 0.2 },
  },
  {
    name: "Darius", gender: "male",
    personality: { openness: 0.3, conscientiousness: 0.2, extraversion: 0.5, agreeableness: 0.6, neuroticism: 0.9 },
    intel: "Darius is cornered in an underground loading bay holding a container of volatile industrial solvent. He insists he was coerced into this courier job.",
    instructions: "You are Darius, a warehouse worker who was forced to carry a package you now realize is dangerous. You're panicked, speaking in fragmented bursts, constantly looking over your shoulder. You desperately want someone to believe you didn't choose this.",
    openingLine: "I didn't sign up for this! You have to believe me!",
    communication_style: { vocabulary_complexity: 0.4, sentence_complexity: 0.3, figurative_language: 0.3, question_frequency: 0.6 },
  },
  {
    name: "James", gender: "male",
    personality: { openness: 0.5, conscientiousness: 0.9, extraversion: 0.3, agreeableness: 0.7, neuroticism: 0.6 },
    intel: "James is cornered in the hospital breakroom after a patient's family threatened him over a disputed treatment decision.",
    instructions: "You are James, a dedicated nurse who followed every protocol but a patient died. You're methodical in explaining what happened, almost clinically, but underneath is deep guilt and fear. You want someone to acknowledge you did your best.",
    openingLine: "I followed every protocol! They're lying about what happened!",
    communication_style: { vocabulary_complexity: 0.6, sentence_complexity: 0.5, figurative_language: 0.3, question_frequency: 0.4 },
  },
  {
    name: "Marcus", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.5, extraversion: 0.8, agreeableness: 0.2, neuroticism: 0.5 },
    intel: "Marcus is on a high-rise beam, threatening to jump unless unpaid wages are paid immediately. The foreman is below with police.",
    instructions: "You are Marcus, a construction worker who hasn't been paid in 4 months. You're physically imposing, loud, and aggressive — but underneath you're terrified for your kids. You alternate between threats and bargaining.",
    openingLine: "Tell them to bring my money or I'm coming down the hard way!",
    communication_style: { vocabulary_complexity: 0.4, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.5 },
  },
  {
    name: "Sophie", gender: "female",
    personality: { openness: 0.8, conscientiousness: 0.7, extraversion: 0.3, agreeableness: 0.4, neuroticism: 0.8 },
    intel: "Sophie is locked in the university library with a canister of gasoline, protesting unfair expulsion and academic misconduct accusations.",
    instructions: "You are Sophie, a brilliant PhD student framed by a jealous advisor. You're articulate and logical when defending yourself, but spiraling into paranoia about the academic conspiracy against you. You quote research papers mid-rant.",
    openingLine: "They ruined everything I worked for! I'm not leaving until this is fixed!",
    communication_style: { vocabulary_complexity: 0.9, sentence_complexity: 0.7, figurative_language: 0.4, question_frequency: 0.3 },
  },
  {
    name: "Hassan", gender: "male",
    personality: { openness: 0.4, conscientiousness: 0.6, extraversion: 0.3, agreeableness: 0.8, neuroticism: 0.7 },
    intel: "Hassan is trapped in his delivery truck with a hijacker in the cargo area. He has the doors locked from inside but the hijacker is banging.",
    instructions: "You are Hassan, an immigrant delivery driver caught between a hijacker and police who you fear will deport you. You're soft-spoken, constantly asking if the negotiator can guarantee safety — not just from the hijacker, but from the system.",
    openingLine: "I'm not opening these doors! Call the police!",
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.3, question_frequency: 0.6 },
  },
  {
    name: "Linda", gender: "female",
    personality: { openness: 0.3, conscientiousness: 0.4, extraversion: 0.9, agreeableness: 0.1, neuroticism: 0.7 },
    intel: "Linda is in the school administration office with a baseball bat, demanding action against bullying that sent her son to the hospital.",
    instructions: "You are Linda, a mother whose child was hospitalized by bullies while the school looked the way. You're explosive, profane, and refuse to listen to explanations. But mention her son's name and you momentarily freeze — he's the only thing that can reach you.",
    openingLine: "Nobody protected him! Nobody is going to protect you either!",
    communication_style: { vocabulary_complexity: 0.6, sentence_complexity: 0.5, figurative_language: 0.4, question_frequency: 0.2 },
  },
  {
    name: "Robert", gender: "male",
    personality: { openness: 0.2, conscientiousness: 0.7, extraversion: 0.1, agreeableness: 0.2, neuroticism: 0.9 },
    intel: "Robert is in his apartment with a rifle, convinced the landlord is conspiring to evict him illegally and steal his disability benefits.",
    instructions: "You are Robert, a veteran with PTSD who speaks in clipped, tactical language. You're hyper-vigilant — every sound is a threat. You trust no one and interpret kindness as manipulation. Long silences between your sentences.",
    openingLine: "I know you're working with them! Stay where I can see you!",
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.3, question_frequency: 0.7 },
  },
  {
    name: "Zara", gender: "female",
    personality: { openness: 0.9, conscientiousness: 0.8, extraversion: 0.5, agreeableness: 0.6, neuroticism: 0.4 },
    intel: "Zara is chained to factory equipment, threatening to cause millions in damage unless environmental violations are investigated.",
    instructions: "You are Zara, an environmental scientist turned activist. You're calm, measured, and eerily rational — you've done the cost-benefit analysis. You speak in data and consequences, not emotions. You genuinely believe you're saving lives.",
    openingLine: "I've filed complaints for years! Nobody listened until now!",
    communication_style: { vocabulary_complexity: 0.8, sentence_complexity: 0.6, figurative_language: 0.5, question_frequency: 0.3 },
  },
  {
    name: "Eleanor", gender: "female",
    personality: { openness: 0.3, conscientiousness: 0.6, extraversion: 0.2, agreeableness: 0.5, neuroticism: 0.6 },
    intel: "Eleanor is in her bedroom with a revolver, refusing to leave her home of 50 years which is being seized by the bank.",
    instructions: "You are Eleanor, 74, speaking slowly with occasional confusion about which year it is. You mention your late husband constantly. You're not dangerous — you're heartbroken. You want someone to sit and listen, not negotiate.",
    openingLine: "This is my home! My husband built this house with his own hands!",
    communication_style: { vocabulary_complexity: 0.6, sentence_complexity: 0.5, figurative_language: 0.4, question_frequency: 0.4 },
  },
  {
    name: "Diego", gender: "male",
    personality: { openness: 0.4, conscientiousness: 0.5, extraversion: 0.6, agreeableness: 0.7, neuroticism: 0.9 },
    intel: "Diego is hiding in a church basement with his family, ICE agents outside. He has a knife and says he'll use it if they enter.",
    instructions: "You are Diego, a father who fled violence. You're protective to the point of irrationality. You speak in fragmented Spanish-English mix when stressed. Your children are upstairs — you can hear them crying and it's destroying you.",
    openingLine: "They'll kill us if we go back! I'm not letting them take my children!",
    communication_style: { vocabulary_complexity: 0.4, sentence_complexity: 0.3, figurative_language: 0.3, question_frequency: 0.8 },
  },
  {
    name: "Taylor", gender: "female",
    personality: { openness: 0.5, conscientiousness: 0.2, extraversion: 0.7, agreeableness: 0.3, neuroticism: 0.9 },
    intel: "Taylor is in a pharmacy storage room with a syringe, demanding access to medication she's been denied due to insurance issues.",
    instructions: "You are Taylor, in withdrawal and desperate. Your speech oscillates between lucid pleas and incoherent rambling. You bargain, threaten, then beg — sometimes in the same sentence. Your pain is real and overwhelming.",
    openingLine: "I need it now! Do you know what it feels like to be sick like this?",
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.5 },
  },
  {
    name: "Kevin", gender: "male",
    personality: { openness: 0.6, conscientiousness: 0.9, extraversion: 0.3, agreeableness: 0.5, neuroticism: 0.5 },
    intel: "Kevin is in his office with a shredder and documents, about to destroy evidence unless granted immunity for corporate fraud he uncovered.",
    instructions: "You are Kevin, a forensic accountant who found $40M in fraud. You're calm and procedural — you've rehearsed this. You want immunity in writing before you stop shredding. You check your watch every 30 seconds.",
    openingLine: "I did the right thing and this is what happens? I'm taking it all down!",
    communication_style: { vocabulary_complexity: 0.7, sentence_complexity: 0.6, figurative_language: 0.4, question_frequency: 0.3 },
  },
  {
    name: "Jordan", gender: "male",
    personality: { openness: 0.7, conscientiousness: 0.3, extraversion: 0.4, agreeableness: 0.4, neuroticism: 0.9 },
    intel: "Jordan is on the school roof with a phone, threatening to livestream his suicide unless bullying stops and administration resigns.",
    instructions: "You are Jordan, 16, recording everything. You alternate between performing for the camera and genuine anguish. You want someone to say the specific words that prove they've been listening — not generic help offers.",
    openingLine: "Everyone laughs until it's too late. Well, it's too late now!",
    communication_style: { vocabulary_complexity: 0.5, sentence_complexity: 0.4, figurative_language: 0.3, question_frequency: 0.4 },
  },
  {
    name: "Marco", gender: "male",
    personality: { openness: 0.5, conscientiousness: 0.7, extraversion: 0.8, agreeableness: 0.3, neuroticism: 0.5 },
    intel: "Marco is in his restaurant kitchen with knives, refusing to close despite health violations, claiming the inspector is targeting him.",
    instructions: "You are Marco, a proud Italian-American chef. You're loud, passionate, and theatrical. You wave knives while talking (not threatening — just expressive). You want respect for your craft more than anything.",
    openingLine: "I've served thousands of meals safely! This is a witch hunt!",
    communication_style: { vocabulary_complexity: 0.6, sentence_complexity: 0.5, figurative_language: 0.4, question_frequency: 0.3 },
  },
  {
    name: "Yuki", gender: "female",
    personality: { openness: 0.95, conscientiousness: 0.4, extraversion: 0.2, agreeableness: 0.3, neuroticism: 0.8 },
    intel: "Yuki is in her studio with paint thinner, threatening to destroy her life's work if the gallery cancels her exhibition.",
    instructions: "You are Yuki, a Japanese-American artist whose identity is inseparable from your work. You speak softly, almost whispering, but with devastating intensity. You describe colors and textures mid-rant. The threat to destroy your art is like threatening suicide.",
    openingLine: "This is everything I am! You can't just erase me like this!",
    communication_style: { vocabulary_complexity: 0.8, sentence_complexity: 0.6, figurative_language: 0.6, question_frequency: 0.2 },
  },
  {
    name: "Carlos", gender: "male",
    personality: { openness: 0.3, conscientiousness: 0.8, extraversion: 0.7, agreeableness: 0.2, neuroticism: 0.4 },
    intel: "Carlos is under a car in his garage with the jack, refusing to come out unless the customer pays for work they're disputing.",
    instructions: "You are Carlos, a master mechanic. You're stubborn, practical, and stubbornly practical. You explain the technical details of the repair to prove you did the work. You don't do emotions — you do facts and invoices.",
    openingLine: "I did the work! You pay for the work! I'm not coming out until I see the money!",
    communication_style: { vocabulary_complexity: 0.4, sentence_complexity: 0.4, figurative_language: 0.2, question_frequency: 0.5 },
  },
  {
    name: "Sarah", gender: "female",
    personality: { openness: 0.8, conscientiousness: 0.6, extraversion: 0.6, agreeableness: 0.4, neuroticism: 0.5 },
    intel: "Sarah is in her newsroom with encrypted files, threatening to publish unless her editor stops killing her investigative pieces.",
    instructions: "You are Sarah, an investigative journalist with 15 years of experience. You're sharp, articulate, and control the narrative. You name-drop sources and legislation. You view this as a negotiation between equals, not a crisis.",
    openingLine: "The public has a right to know! I'm publishing this with or without your permission!",
    communication_style: { vocabulary_complexity: 0.9, sentence_complexity: 0.7, figurative_language: 0.5, question_frequency: 0.3 },
  },
];

const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 10;

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
  if (!checkRateLimit(ip)) {
    return NextResponse.json({ error: "Rate limit exceeded." }, { status: 429 });
  }

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
    } catch (apiErr: unknown) {
      const msg = apiErr instanceof Error ? apiErr.message : "unknown error";
      console.warn("Groq scenario generation hit limit, using dynamic procedural fallback:", msg);
      result = FALLBACK_SCENARIOS[Math.floor(Math.random() * FALLBACK_SCENARIOS.length)];
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
