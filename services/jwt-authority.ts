import jwt from 'jsonwebtoken';

export interface QueueTokenPayload {
  session_id: string;
  user_id: string;
  drop_id: string;
  bot_score: number;
  pow_verified: boolean;
  exp?: number;
  iat?: number;
}

export interface ClaimTokenPayload {
  user_id: string;
  drop_id: string;
  exp?: number;
  iat?: number;
}

const JWT_SECRET = process.env.JWT_SECRET || 'default-insecure-secret-change-in-prod';

export function generateQueueToken(payload: Omit<QueueTokenPayload, 'exp' | 'iat'>): string {
  return jwt.sign(payload, JWT_SECRET, { 
    expiresIn: '10m',
    algorithm: 'HS256' 
  });
}

export function verifyQueueToken(token: string): QueueTokenPayload {
  try {
    const decoded = jwt.verify(token, JWT_SECRET, { 
      algorithms: ['HS256'] 
    }) as QueueTokenPayload;
    
    return decoded;
  } catch (error) {
    throw new Error('TAMPERED_OR_EXPIRED_TOKEN');
  }
}

export function generateClaimToken(userId: string, dropId: string): string {
  const payload: Omit<ClaimTokenPayload, 'exp' | 'iat'> = {
    user_id: userId,
    drop_id: dropId
  };
  
  return jwt.sign(payload, JWT_SECRET, { 
    expiresIn: '5m',
    algorithm: 'HS256'
  });
}
