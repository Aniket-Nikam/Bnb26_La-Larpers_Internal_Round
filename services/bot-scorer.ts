import { Request } from 'express';

export class BotScorer {
  /**
   * Evaluates an incoming request and PoW solve time to generate a bot score.
   * 
   * @param req Express Request object
   * @param powTimeSpentMs Time spent solving the PoW challenge in milliseconds
   * @returns An object containing a normalized score (0.0 to 1.0) and flagged reasons.
   */
  public evaluateRequest(req: Request, powTimeSpentMs: number): { score: number, flags: string[] } {
    let score = 0.0;
    const flags: string[] = [];

    // 1. Missing user-agent (+0.4 risk)
    const userAgent = req.headers['user-agent'];
    if (!userAgent) {
      score += 0.4;
      flags.push('Missing user-agent');
    }

    // 2. Header order anomalies / missing common browser headers (+0.2 risk)
    // Most browsers send Accept and Accept-Language. Their absence suggests a programmatic script.
    if (!req.headers['accept'] || !req.headers['accept-language']) {
      score += 0.2;
      flags.push('Header anomalies detected');
    }

    // 3. Datacenter ASN/IP detection (+0.3 risk)
    const clientIp = req.ip || req.socket.remoteAddress || '';
    if (this.isDatacenterIp(clientIp)) {
      score += 0.3;
      flags.push('Datacenter ASN/IP detection');
    }

    // 4. PoW solving speed (+0.5 risk)
    // If difficulty = 4 solved in < 15ms (impossible for standard CPU JS single-thread)
    if (powTimeSpentMs < 15) {
      score += 0.5;
      flags.push('PoW solving speed impossible for standard CPU JS single-thread');
    }

    // Normalize cumulative score between 0.0 (Pure Human) and 1.0 (Definite Bot)
    const finalScore = Math.min(Math.max(score, 0.0), 1.0);

    return {
      score: finalScore,
      flags
    };
  }

  /**
   * Stub method for Datacenter IP detection.
   * In a real environment, integrate with a database like MaxMind or IP2Location.
   */
  private isDatacenterIp(ip: string): boolean {
    // Basic mock implementation for common cloud provider IP ranges
    if (ip.startsWith('3.') || ip.startsWith('34.') || ip.startsWith('35.') || ip.startsWith('54.')) {
      return true;
    }
    return false;
  }
}
