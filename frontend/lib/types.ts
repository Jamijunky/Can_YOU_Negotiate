export interface PersonalityTraits {
  openness: number;        // 0-1: creativity, curiosity vs. cautious, conventional
  conscientiousness: number; // 0-1: organized, disciplined vs. impulsive, careless
  extraversion: number;    // 0-1: outgoing, energetic vs. solitary, reserved
  agreeableness: number;   // 0-1: trusting, cooperative vs. suspicious, antagonistic
  neuroticism: number;     // 0-1: anxious, volatile vs. calm, confident
}

export interface Scenario {
  name: string;
  gender: "male" | "female";
  personality: PersonalityTraits;
  intel: string;
  instructions: string;
  openingLine: string;
  communicationStyle?: {
    vocabularyComplexity: number;
    sentenceComplexity: number;
    figurativeLanguage: number;
    questionFrequency: number;
  };
}

export interface ScenarioData extends Scenario {
  difficulty?: string;
  dynamicScenario?: boolean;
  age?: string;
  profession?: string;
  motive?: string;
}

export interface TranscriptItem {
  id: string;
  speaker: "user" | "agent";
  senderName: string;
  text: string;
  timestamp: string;
  isFinal: boolean;
  finalizedAt: number;
}

export interface StatusMessage {
  type: "surrender" | "escalate" | "stress" | "report" | "relationship";
  level?: number;
  content?: string;
}

export interface Relationship {
  rapport: number;          // 0-100: emotional connection
  trust: number;            // 0-100: belief in negotiator honesty
  compliancePressure: number; // 0-100: resistance to demands (higher = more resistant)
  cooperationLevel: number; // 0-100: willingness to work together
}

export type EscalationStage = 0 | 1 | 2 | 3 | 4;

export interface EscalationState {
  stage: EscalationStage;
  label: string;
  description: string;
  turnsInStage: number;
  totalTurns: number;
}

export const ESCALATION_STAGE_LABELS: Record<EscalationStage, { label: string; color: string; description: string }> = {
  0: { label: "GUARDED", color: "#22c55e", description: "Wary but communicative. Testing the negotiator." },
  1: { label: "AGITATED", color: "#d99a4e", description: "Raising voice. Making demands. Frustration building." },
  2: { label: "HOSTILE", color: "#f97316", description: "Threatening language. Distrustful. Combatitive." },
  3: { label: "CRISIS", color: "#dc2626", description: "Imminent danger. Erratic. Barely reasoning." },
  4: { label: "CRITICAL", color: "#7f1d1d", description: "About to harm self or others. Last moments." },
};

export interface CoachingHint {
  id: string;
  text: string;
  category: "empathy" | "patience" | "technique" | "warning" | "opportunity";
  timestamp: number;
}

export interface TranscriptMessage {
  type: "transcript";
  id?: string;
  speaker: "user" | "agent";
  senderName?: string;
  text: string;
  isFinal?: boolean;
}

export type PersonaKey =
  | "robber"
  | "scammed"
  | "founder"
  | "teacher"
  | "nurse"
  | "construction"
  | "student"
  | "driver"
  | "parent"
  | "veteran"
  | "activist"
  | "elder"
  | "immigrant"
  | "addict"
  | "whistleblower"
  | "teenager"
  | "chef"
  | "artist"
  | "mechanic"
  | "journalist"
  | "custom";

export type Difficulty = "low" | "medium" | "high";

export type VoiceAssistantState = "connecting" | "listening" | "speaking" | "thinking" | "idle";

export interface TokenRequest {
  room: string;
  username: string;
  metadata: string;
}

export interface TokenResponse {
  token: string;
  error?: string;
}

export interface ScenarioRequest {
  persona: PersonaKey;
  difficulty: Difficulty;
  customMotive?: string;
}

export interface ScenarioResponse extends Scenario {
  error?: string;
}

export interface KeepAliveResponse {
  status: "ok" | "error";
  target_status?: number;
  message?: string;
}
