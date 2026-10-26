export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string;
  timezone: string;
  created_at: string;
  telegram_linked: boolean;
  telegram_username: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name?: string;
  timezone?: string;
}
