import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';

/** find-background 비교표: 후보를 실제 컷 위에 얹어 찍은 스틸을 4×3 으로. 번호·제목·라이선스 */
export const BgSheet: React.FC<{items: {file: string; title: string; license: string}[]}> = ({items = []}) => (
	<AbsoluteFill style={{background: '#1d1420', padding: 24, display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gridTemplateRows: 'repeat(3, minmax(0, 1fr))', gap: 16, fontFamily: 'Galmuri11, sans-serif'}}>
		{items.map((it, i) => (
			<div key={i} style={{display: 'flex', flexDirection: 'column', gap: 6, minHeight: 0}}>
				<div style={{position: 'relative', flex: 1, minHeight: 0}}>
					<Img src={staticFile(it.file)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
					<div style={{position: 'absolute', left: 6, top: 6, background: '#ff7eb6', color: '#fff', font: '700 34px GalmuriStampBold, Galmuri11, sans-serif', padding: '2px 12px', borderRadius: 10}}>{i}</div>
				</div>
				<div style={{color: '#ffe0ef', fontSize: 15, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{it.title || '(제목 없음)'}</div>
				<div style={{color: '#b99', fontSize: 13}}>{it.license}</div>
			</div>
		))}
	</AbsoluteFill>
);
