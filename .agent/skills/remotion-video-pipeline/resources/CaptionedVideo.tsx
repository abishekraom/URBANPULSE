import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig, Video } from 'remotion';
import { loadFont } from "@remotion/google-fonts/inter";
import React from 'react';

const { fontFamily } = loadFont();

interface CaptionedVideoProps {
    videoSrc: string;
    audioSrc: string;
    transcript: {
        segments: Array<{
            start: number;
            end: number;
            text: string;
            words: Array<{
                word: string;
                start: number;
                end: number;
            }>
        }>
    };
}

export const CaptionedVideo: React.FC<CaptionedVideoProps> = ({ videoSrc, audioSrc, transcript }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Flatten words for easier processing
    const allWords = transcript.segments.flatMap(s => s.words || []);

    const getCurrentWordIndex = () => {
        const currentTime = frame / fps;
        return allWords.findIndex(w => currentTime >= w.start && currentTime <= w.end);
    };

    const currentWordIndex = getCurrentWordIndex();
    
    // Chunking: 4 words per chunk. Find which chunk current time belongs to.
    // If between words, use the next word's chunk or previous.
    // Logic: Look for the word that is active, or the closest one.
    
    const relevantWordIndex = currentWordIndex !== -1 ? currentWordIndex : allWords.findIndex(w => (frame / fps) < w.start);
    const chunkIndex = Math.floor((relevantWordIndex === -1 ? allWords.length : relevantWordIndex) / 4);
    const chunkStart = chunkIndex * 4;
    const currentChunk = allWords.slice(chunkStart, chunkStart + 4);

    return (
        <AbsoluteFill style={{ backgroundColor: 'black' }}>
            {/* 1. Muted Original Video */}
            <Video src={videoSrc} muted />

            {/* 2. Processed Audio */}
            {audioSrc && <Audio src={audioSrc} />}

            {/* 3. Gradient Overlay */}
            <AbsoluteFill
                style={{
                    background: 'linear-gradient(to top, rgba(0,0,0,0.85), transparent)',
                    height: '40%',
                    top: '60%'
                }}
            />

            {/* 4. Captions */}
            <div
                style={{
                    position: 'absolute',
                    bottom: 120,
                    width: '100%',
                    textAlign: 'center',
                    fontFamily,
                    fontSize: 72,
                    fontWeight: 800,
                    letterSpacing: '0.02em',
                    display: 'flex',
                    justifyContent: 'center',
                    gap: 24, // Word gap
                    textShadow: '0 4px 20px rgba(0,0,0,0.8)',
                    padding: '0 40px'
                }}
            >
                {currentChunk.map((wordObj, i) => {
                    const globalIndex = chunkStart + i;
                    const currentTime = frame / fps;
                    
                    let style: React.CSSProperties = {};
                    
                    if (globalIndex === currentWordIndex) {
                        // Current Word
                        style = {
                            color: '#BFF549',
                            textShadow: '0 0 40px rgba(191,245,73,0.8)',
                            transform: 'scale(1.1)',
                            display: 'inline-block' // needed for transform
                        };
                    } else if (currentTime > wordObj.end) {
                        // Past
                        style = {
                            color: '#FFFFFF'
                        };
                    } else {
                        // Future
                        style = {
                            color: 'rgba(255,255,255,0.5)'
                        };
                    }

                    // Cleanup: remove trailing punctuation
                    const cleanText = wordObj.word.replace(/[.,]+$/, '');

                    return (
                        <span key={globalIndex} style={style}>
                            {cleanText}
                        </span>
                    );
                })}
            </div>
        </AbsoluteFill>
    );
};
