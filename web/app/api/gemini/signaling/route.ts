import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  try {
    const { sdp, type, tools, system_instruction } = await req.json();
    if (!sdp || !type) {
      return NextResponse.json({ error: 'Missing SDP offer' }, { status: 400 });
    }

    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: 'Server missing GEMINI_API_KEY' }, { status: 500 });
    }

    const model = process.env.GEMINI_REALTIME_MODEL || 'gemini-live-2.5-flash-preview';

    // Transform incoming tools into Gemini functionDeclarations shape
    const transformedTools = Array.isArray(tools)
      ? tools.map((t: any) => ({
          functionDeclarations: [
            {
              name: t.name,
              description: t.description,
              parameters: t.parameters || { type: 'object', properties: {} },
            },
          ],
        }))
      : [];

    const body = {
      offer: { type, sdp },
      tools: transformedTools,
      responseModality: 'AUDIO',
      systemInstruction: { parts: [{ text: String(system_instruction || '') }] },
    };

    // Attempt 1: v1beta with x-goog-api-key
    const urlV1beta = `https://generativelanguage.googleapis.com/v1beta/models/${model}:openSession`;
    const attempt1 = await fetch(urlV1beta, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-goog-api-key': apiKey,
      },
      body: JSON.stringify(body),
    });
    const t1 = await attempt1.text();

    let json: any = {};
    if (!attempt1.ok) {
      // Attempt 2: v1beta with Authorization Bearer
      const attempt2 = await fetch(urlV1beta, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`,
        },
        body: JSON.stringify(body),
      });
      const t2 = await attempt2.text();

      if (!attempt2.ok) {
        // Attempt 3: v1alpha realtime open_session (legacy)
        const urlV1alpha = 'https://generativelanguage.googleapis.com/realtime/v1alpha/open_session';
        const legacyBody = {
          model,
          ...body,
        };
        const attempt3 = await fetch(urlV1alpha, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`,
          },
          body: JSON.stringify(legacyBody),
        });
        const t3 = await attempt3.text();
        if (!attempt3.ok) {
          return NextResponse.json({
            error: 'Gemini session failed',
            detail: JSON.stringify({
              attempt1: { status: attempt1.status, body: t1?.slice(0, 500) },
              attempt2: { status: attempt2.status, body: t2?.slice(0, 500) },
              attempt3: { status: attempt3.status, body: t3?.slice(0, 500) },
            }),
          }, { status: 500 });
        }
        json = JSON.parse(t3 || '{}');
      } else {
        json = JSON.parse(t2 || '{}');
      }
    } else {
      json = JSON.parse(t1 || '{}');
    }

    const answer = json?.answer;
    if (!answer?.sdp || !answer?.type) {
      return NextResponse.json({ error: 'Invalid answer from Gemini', detail: json }, { status: 500 });
    }
    // Return only the RTC answer to keep client simple
    return NextResponse.json({ sdp: answer.sdp, type: answer.type });
  } catch (e: any) {
    return NextResponse.json({ error: e?.message || 'Unknown error' }, { status: 500 });
  }
}


