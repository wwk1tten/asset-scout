import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';

type Item = {model: string; title: string; license: string};
type Loaded = {item: Item; obj: THREE.Object3D; tris: number; fixed: string[]};

/**
 * 3D 후보(glb/gltf) 테스트: 크기 맞춤 + 빙글빙글. 자동 정리:
 *  삼각형 maxTris 넘으면 뺌 / 로드 실패 뺌 / 눕혀 온 건 세움 / 바닥판(납작하고 넓은 메시) 숨김 / 금속 1 → 0(검게 나오는 것)
 * 남은 것만 4열로 다시 깐다(최대 16개).
 */
export const PropGrid: React.FC<{items: Item[]; spin: number; maxTris: number}> = ({items = [], spin = 1, maxTris = 50000}) => {
	const frame = useCurrentFrame();
	const [loaded, setLoaded] = useState<Loaded[] | null>(null);
	useEffect(() => {
		const h = delayRender('props');
		Promise.all(items.map((it) => new GLTFLoader().loadAsync(staticFile(it.model)).then((g): Loaded | null => {
			const obj = g.scene;
			const fixed: string[] = [];
			let tris = 0;
			obj.updateMatrixWorld(true);
			const all = new THREE.Box3().setFromObject(obj), allSize = all.getSize(new THREE.Vector3());
			const big = Math.max(allSize.x, allSize.y, allSize.z);
			obj.traverse((o) => {
				const m = o as THREE.Mesh;
				if (!m.isMesh) return;
				m.frustumCulled = false;
				tris += (m.geometry.index ? m.geometry.index.count : m.geometry.attributes.position.count) / 3;
				const b = new THREE.Box3().setFromObject(m).getSize(new THREE.Vector3());
				const dims = [b.x, b.y, b.z].sort((p, q) => p - q);
				if (dims[0] < big * 0.01 && dims[1] > big * 0.6) { m.visible = false; if (!fixed.includes('바닥판 숨김')) fixed.push('바닥판 숨김'); }
				for (const mat of ([] as THREE.Material[]).concat(m.material)) {
					const s = mat as THREE.MeshStandardMaterial;
					if (s.metalness !== undefined && s.metalness > 0.8) { s.metalness = 0; if (!fixed.includes('금속 보정')) fixed.push('금속 보정'); }
				}
			});
			if (tris > maxTris) return null;
			// 보이는 메시만으로 다시 재서 세우기·크기 맞춤
			const vis = new THREE.Box3();
			obj.traverse((o) => { const m = o as THREE.Mesh; if (m.isMesh && m.visible) vis.expandByObject(m); });
			let size = vis.getSize(new THREE.Vector3());
			const wrap = new THREE.Group(), pivot = new THREE.Group();
			pivot.add(obj);
			if (size.z > size.y * 1.4 && size.z >= size.x) { pivot.rotation.x = -Math.PI / 2; fixed.push('세움'); }
			pivot.updateMatrixWorld(true);
			const box = new THREE.Box3();
			obj.traverse((o) => { const m = o as THREE.Mesh; if (m.isMesh && m.visible) box.expandByObject(m); });
			size = box.getSize(new THREE.Vector3());
			const c = box.getCenter(new THREE.Vector3());
			pivot.position.sub(c);
			wrap.add(pivot);
			wrap.scale.setScalar(0.5 / Math.max(size.x, size.y, size.z));
			return {item: it, obj: wrap, tris: Math.round(tris), fixed};
		}, () => null))).then((r) => { setLoaded(r.filter((x): x is Loaded => !!x).slice(0, 16)); continueRender(h); }, (e) => cancelRender(e));
	}, [items, maxTris]);
	if (!loaded) return null;
	const rows = Math.ceil(loaded.length / 4) || 1;
	const rowH = 1920 / Math.max(rows, 3);
	const pos = (i: number): [number, number, number] => [((i % 4) - 1.5) * 0.66, (2.41 * (960 - (Math.floor(i / 4) + 0.42) * rowH)) / 960, 0];
	return (
		<AbsoluteFill style={{background: 'linear-gradient(180deg, #fff6fa 0%, #ffe6f0 100%)'}}>
			<ThreeCanvas width={1080} height={1920} camera={{fov: 30, position: [0, 0, 9], near: 0.1, far: 50}} gl={{alpha: true, antialias: true}}>
				<Draw />
				<ambientLight intensity={2.3} color="#ffffff" />
				<directionalLight position={[2, 4, 3]} intensity={2.4} color="#ffffff" />
				<directionalLight position={[-3, 2, -2]} intensity={0.9} color="#ffe6f0" />
				{loaded.map((l, i) => <group key={i} position={pos(i)} rotation={[0.15, (frame / 30) * spin, 0]}><primitive object={l.obj} /></group>)}
			</ThreeCanvas>
			{loaded.map((l, i) => (
				<div key={i} style={{position: 'absolute', left: `${(i % 4) * 25}%`, width: '25%', top: (Math.floor(i / 4) + 0.42) * rowH + 140, textAlign: 'center', fontFamily: 'Galmuri11, sans-serif', color: '#3a2140', padding: '0 8px'}}>
					<div style={{font: '700 34px GalmuriStampBold, Galmuri11, sans-serif', color: '#d6457f'}}>{i}</div>
					<div style={{fontSize: 19, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{l.item.title}</div>
					<div style={{fontSize: 16, color: '#7a5a6e'}}>{(l.tris / 1000).toFixed(1)}k tris{l.fixed.length ? ` · ${l.fixed.join(', ')}` : ''}</div>
					<div style={{fontSize: 15, color: '#9a7d8e'}}>{l.item.license}</div>
				</div>
			))}
		</AbsoluteFill>
	);
};

// Remotion 이 rAF 를 막아 R3F 자동 렌더가 안 돈다 → 커밋마다 그린다
const Draw: React.FC = () => {
	const {gl, scene, camera} = useThree();
	useEffect(() => { gl.render(scene, camera); });
	return null;
};
