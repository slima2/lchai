import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../auth/AuthProvider';
import { getCaseGraph, rebuildGraph, explainGraph } from '../api';
import * as d3 from 'd3';

function escapeXmlContent(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

function toNCName(s: string): string {
  return s.replace(/[^a-zA-Z0-9_.-]/g, '_').replace(/^[^a-zA-Z_]/, '_$&');
}

function safeIri(iri: string): string {
  return iri.replace(/ /g, '%20').replace(/[<>"{}|\\^`]/g, (c) => encodeURIComponent(c));
}

const NODE_COLORS: Record<string, string> = {
  Case: '#3B82F6',
  Gene: '#EF4444',
  Diagnosis: '#10B981',
  Pattern: '#F59E0B',
  Stage: '#06B6D4',
  Mutation: '#EF4444',
  Treatment: '#8B5CF6',
  Ontology: '#78909C',
  entity: '#8B5CF6',
  case: '#3B82F6',
  gene: '#EF4444',
  diagnosis: '#10B981',
  pattern: '#F59E0B',
  treatment: '#8B5CF6',
  stage: '#06B6D4',
  curated: '#78909C',
};

const NODE_RADIUS: Record<string, number> = {
  Case: 24,
  Gene: 18,
  Pattern: 18,
  Diagnosis: 20,
  Stage: 16,
  Mutation: 18,
  Treatment: 16,
  Ontology: 14,
  case: 24,
  gene: 18,
  pattern: 18,
  diagnosis: 20,
  stage: 16,
  treatment: 16,
};

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  type: string;
  label: string;
  color?: string;
  score?: number;
}

interface GraphEdge extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  label?: string;
  provenance?: string;
  asserted?: boolean;
}

interface Props {
  caseId: string;
  resultBundleId?: string | null;
}

export default function GraphPanel({ caseId, resultBundleId }: Props) {
  const { preferredLanguage } = useAuth();
  const qc = useQueryClient();
  const [showInferred, setShowInferred] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const graph = useQuery({
    queryKey: ['graph', caseId, resultBundleId],
    queryFn: async () => {
      await rebuildGraph(caseId);
      return getCaseGraph(caseId).then(r => r.data);
    },
  });

  const rebuild = useMutation({
    mutationFn: () => rebuildGraph(caseId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['graph', caseId, resultBundleId] }),
  });

  const explain = useMutation({
    mutationFn: () => explainGraph(caseId, preferredLanguage).then(r => r.data),
  });

  const handleFitGraph = useCallback(() => {
    const el = svgRef.current as any;
    if (!el?.__zoom_behavior || !el?.__svg_selection) return;
    const gEl = el.querySelector('g');
    if (!gEl) return;
    const bounds = gEl.getBBox();
    const width = containerRef.current?.clientWidth || 900;
    const height = isFullscreen ? (window.innerHeight - 120) : 700;
    if (bounds.width <= 0) return;
    const pad = 80;
    const scaleX = width / (bounds.width + pad * 2);
    const scaleY = height / (bounds.height + pad * 2);
    const scale = Math.min(scaleX, scaleY, 1.2);
    const tx = width / 2 - (bounds.x + bounds.width / 2) * scale;
    const ty = height / 2 - (bounds.y + bounds.height / 2) * scale;
    el.__svg_selection.transition().duration(400).call(
      el.__zoom_behavior.transform,
      d3.zoomIdentity.translate(tx, ty).scale(scale)
    );
  }, [isFullscreen]);

  const handleExportOwl = useCallback(() => {
    const nodes: any[] = graph.data?.nodes || [];
    const edges: any[] = graph.data?.edges || [];
    if (nodes.length === 0) return;

    const baseNs = 'http://lchai.gptfy.biz/ontology#';

    const nodeIri = (n: any) => safeIri(n.iri || `${baseNs}${encodeURIComponent(n.id)}`);

    const lines: string[] = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<rdf:RDF',
      '  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"',
      '  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"',
      '  xmlns:owl="http://www.w3.org/2002/07/owl#"',
      '  xmlns:xsd="http://www.w3.org/2001/XMLSchema#"',
      `  xmlns:lchai="${baseNs}"`,
      '  xmlns:ncit="http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#"',
      '>',
      '',
      `  <owl:Ontology rdf:about="${safeIri(baseNs + 'case-graph-' + caseId)}"/>`,
      '',
    ];

    // Declare classes for each node type
    const types = new Set(nodes.map((n: any) => n.type || 'Entity'));
    for (const t of types) {
      lines.push(`  <owl:Class rdf:about="${baseNs}${toNCName(t)}"/>`);
    }
    lines.push('');

    // Declare object properties for each edge type
    const predicates = new Set(edges.map((e: any) => e.type || e.label || 'relatedTo'));
    for (const p of predicates) {
      lines.push(`  <owl:ObjectProperty rdf:about="${baseNs}${toNCName(p)}"/>`);
    }
    lines.push('');

    // Individuals
    for (const n of nodes) {
      const iri = nodeIri(n);
      lines.push(`  <owl:NamedIndividual rdf:about="${iri}">`);
      lines.push(`    <rdfs:label>${escapeXmlContent(n.label || n.id)}</rdfs:label>`);
      lines.push(`    <rdf:type rdf:resource="${baseNs}${toNCName(n.type || 'Entity')}"/>`);
      if (n.score !== undefined) {
        lines.push(`    <lchai:score rdf:datatype="http://www.w3.org/2001/XMLSchema#float">${n.score}</lchai:score>`);
      }
      lines.push('  </owl:NamedIndividual>');
      lines.push('');
    }

    // Relationships (no XML comments to avoid -- issues)
    const nodeById = new Map(nodes.map((n: any) => [n.id, n]));
    for (const e of edges) {
      const srcId = typeof e.source === 'string' ? e.source : e.source?.id;
      const tgtId = typeof e.target === 'string' ? e.target : e.target?.id;
      const srcNode = nodeById.get(srcId);
      const tgtNode = nodeById.get(tgtId);
      if (!srcNode || !tgtNode) continue;
      const srcIri = nodeIri(srcNode);
      const tgtIri = nodeIri(tgtNode);
      const predicate = toNCName(e.type || e.label || 'relatedTo');

      lines.push(`  <rdf:Description rdf:about="${srcIri}">`);
      lines.push(`    <lchai:${predicate} rdf:resource="${tgtIri}"/>`);
      lines.push('  </rdf:Description>');
      lines.push('');
    }

    lines.push('</rdf:RDF>');

    const blob = new Blob([lines.join('\n')], { type: 'application/rdf+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lchai_case_graph_${caseId.slice(0, 8)}.owl`;
    a.click();
    URL.revokeObjectURL(url);
  }, [graph.data, caseId]);

  const rawNodes: GraphNode[] = (graph.data?.nodes || []).map((n: any) => ({
    ...n,
    color: n.color || NODE_COLORS[n.type] || '#999',
  }));

  const rawEdges: GraphEdge[] = (graph.data?.edges || []).filter(
    (e: any) => showInferred || (e.asserted !== false && e.type !== 'inferred')
  );

  // D3 force-directed simulation
  useEffect(() => {
    if (!svgRef.current || rawNodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    const width = containerRef.current?.clientWidth || 900;
    const height = isFullscreen ? (window.innerHeight - 120) : 700;

    svg.attr('width', width).attr('height', height);
    svg.selectAll('*').remove();

    // Build node map for edge resolution
    const nodeMap = new Map(rawNodes.map(n => [n.id, n]));

    // Deep copy nodes & edges for simulation
    const nodes: GraphNode[] = rawNodes.map(n => ({ ...n }));
    const edges: GraphEdge[] = rawEdges
      .filter((e: any) => {
        const src = typeof e.source === 'string' ? e.source : (e.source as any)?.id;
        const tgt = typeof e.target === 'string' ? e.target : (e.target as any)?.id;
        return nodeMap.has(src) && nodeMap.has(tgt);
      })
      .map((e: any) => ({ ...e }));

    // Hierarchical layer assignment: Case → Patterns → Diagnosis → Genes → Ontology → Treatments
    const LAYER_ORDER: Record<string, number> = {
      Case: 0, case: 0,
      Pattern: 1, pattern: 1,
      Diagnosis: 2, diagnosis: 2,
      Gene: 3, gene: 3, Mutation: 3,
      Stage: 3, stage: 3,
      Ontology: 4, curated: 4,
      Treatment: 5, treatment: 5,
    };
    const layerCount = 6;
    const layerSpacing = height / (layerCount + 1);

    // Group nodes by layer for horizontal distribution
    const layerBuckets: Map<number, GraphNode[]> = new Map();
    for (const n of nodes) {
      const layer = LAYER_ORDER[n.type] ?? 3;
      if (!layerBuckets.has(layer)) layerBuckets.set(layer, []);
      layerBuckets.get(layer)!.push(n);
    }

    // Estimate label width for spacing (approx 6px per char at 10px font)
    const labelWidth = (n: GraphNode) => {
      const text = n.label || n.id;
      return Math.max((text.length > 30 ? 30 : text.length) * 6 + 20, 60);
    };

    // Assign initial x,y positions in a grid per layer with label-aware spacing
    for (const [layer, bucket] of layerBuckets) {
      const yTarget = layerSpacing * (layer + 1);
      const totalWidth = bucket.reduce((sum, n) => sum + labelWidth(n), 0);
      const margin = 60;
      const availableWidth = width - margin * 2;
      const scale = totalWidth > availableWidth ? availableWidth / totalWidth : 1;
      let xCursor = (width - totalWidth * scale) / 2;
      bucket.forEach((n) => {
        const w = labelWidth(n) * scale;
        n.x = xCursor + w / 2;
        n.y = yTarget;
        xCursor += w;
      });
    }

    // Definitions (arrow markers)
    const defs = svg.append('defs');

    defs.append('marker')
      .attr('id', 'arrow-asserted')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#6B7280');

    defs.append('marker')
      .attr('id', 'arrow-inferred')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#F59E0B');

    // Container group for zoom/pan
    const g = svg.append('g');

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    svg.call(zoom);

    // Simulation with layered Y constraint and label-aware collision
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, GraphEdge>(edges).id(d => d.id).distance(100).strength(0.2))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('collision', d3.forceCollide<GraphNode>().radius(d => labelWidth(d) / 2).strength(0.9))
      .force('x', d3.forceX(width / 2).strength(0.02))
      .force('y', d3.forceY<GraphNode>((d) => {
        const layer = LAYER_ORDER[d.type] ?? 3;
        return layerSpacing * (layer + 1);
      }).strength(0.85));

    // Draw edges
    const isInferred = (d: any) => d.asserted === false || d.type === 'inferred';
    const link = g.append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', (d: any) => isInferred(d) ? '#F59E0B' : '#9CA3AF')
      .attr('stroke-width', (d: any) => isInferred(d) ? 1.5 : 2)
      .attr('stroke-dasharray', (d: any) => isInferred(d) ? '6,3' : 'none')
      .attr('marker-end', (d: any) => isInferred(d) ? 'url(#arrow-inferred)' : 'url(#arrow-asserted)');

    // Edge labels
    const edgeLabels = g.append('g')
      .selectAll('text')
      .data(edges)
      .join('text')
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('fill', '#6B7280')
      .attr('dy', -6)
      .text((d: any) => d.label || d.type || '');

    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .on('click', (_event: any, d: GraphNode) => {
        setSelectedNode(d);
      })
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as any
      );

    // Node circles
    node.append('circle')
      .attr('r', (d: GraphNode) => NODE_RADIUS[d.type] || 16)
      .attr('fill', (d: GraphNode) => d.color || '#999')
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9);

    // Node labels
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', (d: GraphNode) => (NODE_RADIUS[d.type] || 16) + 14)
      .attr('font-size', '10px')
      .attr('fill', '#374151')
      .attr('font-weight', '500')
      .text((d: GraphNode) => {
        const label = d.label || d.id;
        return label.length > 30 ? label.slice(0, 28) + '...' : label;
      });

    // Store zoom for external buttons
    (svgRef.current as any).__zoom_behavior = zoom;
    (svgRef.current as any).__svg_selection = svg;

    // Node type icon text
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('font-size', '10px')
      .attr('fill', '#fff')
      .attr('font-weight', 'bold')
      .text((d: GraphNode) => {
        const icons: Record<string, string> = {
          Case: 'C', Gene: 'G', Pattern: 'P', Diagnosis: 'D', Stage: 'S', Mutation: 'M',
        };
        return icons[d.type] || d.type[0]?.toUpperCase() || '?';
      });

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      edgeLabels
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    // Auto-fit helper
    const fitToView = () => {
      const bounds = (g.node() as SVGGElement)?.getBBox();
      if (bounds && bounds.width > 0) {
        const pad = 80;
        const scaleX = width / (bounds.width + pad * 2);
        const scaleY = height / (bounds.height + pad * 2);
        const scale = Math.min(scaleX, scaleY, 1.2);
        const tx = width / 2 - (bounds.x + bounds.width / 2) * scale;
        const ty = height / 2 - (bounds.y + bounds.height / 2) * scale;
        svg.transition().duration(500).call(
          zoom.transform,
          d3.zoomIdentity.translate(tx, ty).scale(scale)
        );
      }
    };

    simulation.on('end', fitToView);
    const fitTimer = setTimeout(fitToView, 3000);

    return () => {
      clearTimeout(fitTimer);
      simulation.stop();
    };
  }, [rawNodes.length, rawEdges.length, showInferred, isFullscreen]);

  return (
    <div ref={panelRef} className={isFullscreen ? 'fixed inset-0 z-50 bg-white overflow-auto p-4' : ''}>
      <div className="flex gap-2 mb-4 items-center flex-wrap">
        <button
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700 transition"
          onClick={() => rebuild.mutate()}
          disabled={rebuild.isPending}
        >
          {rebuild.isPending ? 'Rebuilding...' : 'Rebuild Graph'}
        </button>
        <button
          className="bg-amber-500 text-white px-4 py-1.5 rounded text-sm hover:bg-amber-600 transition"
          onClick={() => explain.mutate()}
          disabled={rawNodes.length === 0 || explain.isPending}
        >
          {explain.isPending ? 'Generating...' : 'Explain with AI'}
        </button>
        <button
          className="bg-gray-600 text-white px-3 py-1.5 rounded text-sm hover:bg-gray-700 transition"
          onClick={handleFitGraph}
          disabled={rawNodes.length === 0}
          title="Fit graph to view"
        >
          Fit
        </button>
        <button
          className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 transition"
          onClick={() => setIsFullscreen(f => !f)}
          title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {isFullscreen ? '✕ Exit' : '⛶ Fullscreen'}
        </button>
        <button
          className="bg-emerald-600 text-white px-3 py-1.5 rounded text-sm hover:bg-emerald-700 transition"
          onClick={handleExportOwl}
          disabled={rawNodes.length === 0}
          title="Download graph as OWL/RDF"
        >
          ↓ OWL
        </button>
        <label className="flex items-center gap-1.5 text-sm">
          <input type="checkbox" checked={showInferred} onChange={e => setShowInferred(e.target.checked)} />
          Show inferred edges
        </label>
        <span className="text-xs text-gray-400">
          {rawNodes.length} nodes, {rawEdges.length} edges
        </span>
        {graph.data?.graph_snapshot_id && (
          <span className="text-xs text-gray-400">| Snapshot: {graph.data.graph_snapshot_id.slice(0, 8)}</span>
        )}
        {(graph.data as any)?.graph_source === 'mock' && (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-amber-200 text-amber-900">
            Grafo mockup
          </span>
        )}
      </div>

      {/* Origen del grafo: causa si no viene de Fuseki */}
      {((graph.data as any)?.graph_source_message) && (
        <div className={`mb-3 px-3 py-2 rounded text-xs ${(graph.data as any)?.graph_source === 'mock' ? 'bg-amber-50 border border-amber-300 text-amber-800' : 'bg-blue-50 border border-blue-200 text-blue-800'}`}>
          {(graph.data as any).graph_source_message}
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-4 mb-3 text-xs flex-wrap">
        {Object.entries(NODE_COLORS).filter(([k]) => k[0] === k[0].toUpperCase()).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: color }} />
            {type}
          </div>
        ))}
        <div className="flex items-center gap-1 ml-4">
          <span className="inline-block w-6 border-t-2 border-gray-400" /> Asserted
        </div>
        <div className="flex items-center gap-1">
          <span className="inline-block w-6 border-t-2 border-yellow-500 border-dashed" /> Inferred
        </div>
      </div>

      {/* D3 Force-Directed Graph */}
      <div ref={containerRef} className="border rounded bg-white relative" style={{ minHeight: isFullscreen ? 'calc(100vh - 200px)' : 700 }}>
        {rawNodes.length > 0 ? (
          <>
            <svg ref={svgRef} className="w-full" style={{ minHeight: isFullscreen ? 'calc(100vh - 200px)' : 700 }} />
            {/* Zoom controls */}
            <div className="absolute bottom-3 right-3 flex items-center gap-1 bg-gray-800 rounded-lg shadow-lg px-1 py-1">
              <button
                className="w-8 h-8 flex items-center justify-center text-white text-lg font-bold hover:bg-gray-700 rounded"
                onClick={() => {
                  const el = svgRef.current as any;
                  if (el?.__zoom_behavior && el?.__svg_selection) {
                    el.__svg_selection.transition().duration(300).call(
                      el.__zoom_behavior.scaleBy, 0.7
                    );
                  }
                }}
              >−</button>
              <button
                className="h-8 flex items-center justify-center text-white text-xs font-mono px-2 hover:bg-gray-700 rounded"
                onClick={handleFitGraph}
                title="Fit all nodes"
              >Fit</button>
              <button
                className="w-8 h-8 flex items-center justify-center text-white text-lg font-bold hover:bg-gray-700 rounded"
                onClick={() => {
                  const el = svgRef.current as any;
                  if (el?.__zoom_behavior && el?.__svg_selection) {
                    el.__svg_selection.transition().duration(300).call(
                      el.__zoom_behavior.scaleBy, 1.4
                    );
                  }
                }}
              >+</button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full min-h-[700px] text-gray-400 text-sm">
            {graph.isLoading ? 'Loading graph...' : 'Click "Rebuild Graph" to generate the knowledge graph'}
          </div>
        )}
      </div>

      {/* LLM explanation */}
      <details className="mt-4" open={!!explain.data || explain.isPending}>
        <summary className="text-sm font-semibold cursor-pointer text-gray-600 flex items-center gap-2">
          <span>AI Explanation</span>
          {explain.isPending && (
            <span className="text-xs text-amber-600 animate-pulse">Generando...</span>
          )}
        </summary>
        <div className="mt-2">
          {explain.data && (
            <div className="space-y-2">
              <div className="p-4 bg-amber-50 border border-amber-200 rounded text-sm text-gray-700 whitespace-pre-wrap">
                {explain.data.explanation}
              </div>
              <button
                className="text-xs text-amber-600 hover:underline"
                onClick={() => explain.mutate()}
              >
                Regenerate explanation
              </button>
            </div>
          )}
          {explain.isError && (
            <p className="text-red-600 text-sm">Error generating explanation. Please try again.</p>
          )}
        </div>
      </details>

      {/* Selected node details */}
      {selectedNode && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
          <div className="flex justify-between items-start">
            <div>
              <p className="font-semibold">{selectedNode.label}</p>
              <p className="text-xs text-gray-500">Type: {selectedNode.type} | ID: {selectedNode.id}</p>
              {selectedNode.score !== undefined && (
                <p className="text-xs text-gray-500">Score: {selectedNode.score}</p>
              )}
            </div>
            <button className="text-xs text-blue-600 hover:underline" onClick={() => setSelectedNode(null)}>
              Close
            </button>
          </div>
        </div>
      )}

      {/* Edge list (compact) */}
      <details className="mt-4">
        <summary className="text-sm font-semibold cursor-pointer text-gray-600">
          Edge Details ({rawEdges.length})
        </summary>
        <div className="border rounded mt-2 max-h-48 overflow-y-auto divide-y text-xs">
          {rawEdges.map((e: any, i: number) => {
            const src = typeof e.source === 'string' ? e.source : e.source?.id || '';
            const tgt = typeof e.target === 'string' ? e.target : e.target?.id || '';
            return (
              <div key={i} className="px-3 py-1.5 flex gap-2 items-center">
                <span className="font-mono">{src.split(':').pop()?.slice(0, 12)}</span>
                <span className={`font-bold ${e.asserted === false ? 'text-yellow-600' : 'text-blue-600'}`}>
                  —{e.type}→
                </span>
                <span className="font-mono">{tgt.split(':').pop()?.slice(0, 12)}</span>
                {e.provenance && <span className="text-gray-400 ml-auto">via {e.provenance}</span>}
              </div>
            );
          })}
        </div>
      </details>
    </div>
  );
}
