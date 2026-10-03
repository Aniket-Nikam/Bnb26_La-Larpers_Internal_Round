import { Request, Response, NextFunction } from 'express';
import { randomUUID, randomBytes, createHash } from 'crypto';

interface Challenge {
  seed: string;
  difficulty: number;
  createdAt: number;
  used: boolean;
}

// In-memory map for active challenges.
// In a production distributed environment, use Redis.
const activeChallenges = new Map<string, Challenge>();
const CHALLENGE_TTL_MS = 120 * 1000; // 120 seconds

declare global {
  namespace Express {
    interface Request {
      powVerified?: boolean;
    }
  }
}

export function createChallenge(req: Request, res: Response): Response {
  const challenge_id = randomUUID();
  const seed = randomBytes(32).toString('hex');
  const difficulty = 4;
  const createdAt = Date.now();

  activeChallenges.set(challenge_id, {
    seed,
    difficulty,
    createdAt,
    used: false
  });

  return res.json({
    challenge_id,
    seed,
    difficulty,
    expiresIn: CHALLENGE_TTL_MS
  });
}

export function verifyPoW(req: Request, res: Response, next: NextFunction): Response | void {
  const { challenge_id, nonce, user_id } = req.body;

  if (!challenge_id || nonce === undefined) {
    return res.status(403).json({ error: 'INVALID_POW_SOLUTION' });
  }

  const challenge = activeChallenges.get(challenge_id);

  if (!challenge) {
    return res.status(403).json({ error: 'INVALID_POW_SOLUTION' });
  }

  if (challenge.used) {
    return res.status(403).json({ error: 'INVALID_POW_SOLUTION' });
  }

  if (Date.now() - challenge.createdAt > CHALLENGE_TTL_MS) {
    activeChallenges.delete(challenge_id);
    return res.status(403).json({ error: 'INVALID_POW_SOLUTION' });
  }

  // Immediately mark used to enforce single-use constraint
  challenge.used = true;

  const hash = createHash('sha256')
    .update(challenge.seed + nonce.toString())
    .digest('hex');

  const targetPrefix = '0'.repeat(challenge.difficulty);

  if (!hash.startsWith(targetPrefix)) {
    return res.status(403).json({ error: 'INVALID_POW_SOLUTION' });
  }

  // Attach verified status and proceed
  req.powVerified = true;
  next();
}
