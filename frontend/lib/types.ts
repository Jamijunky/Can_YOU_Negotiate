export interface Scenario {
  name: string;
  gender: "male" | "female";
  archetype: string;
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
}

export interface StatusMessage {
  type: "surrender" | "escalate" | "stress" | "report";
  level?: number;
  content?: string;
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
