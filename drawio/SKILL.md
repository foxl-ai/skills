---
name: drawio
description: "Create and export draw.io diagrams (flowcharts, architecture diagrams, ER diagrams, sequence diagrams, class diagrams). Use when the user asks for any visual diagram, flowchart, or architecture drawing. Triggers on: diagram, drawio, flowchart, architecture diagram, ER diagram, sequence diagram, class diagram, 다이어그램, 플로우차트, 아키텍처 다이어그램."
---

# Draw.io Diagram Skill

Generate draw.io diagrams as native `.drawio` files. Optionally export to PNG, SVG, or PDF with the diagram XML embedded.

## Workflow

1. Generate draw.io XML in mxGraphModel format
2. Write the XML to `~/Desktop/<name>.drawio` using `exec` with `cat << 'EOF' > filename.drawio`
3. If export format requested (png/svg/pdf), export with `--embed-diagram`, then delete the source `.drawio`
4. Open the result with `open <file>`

## draw.io CLI

```bash
# Export
drawio -x -f <format> -e -b 10 -o <output> <input.drawio>
# Flags: -x (export) -f (format: png/svg/pdf) -e (embed-diagram) -b (border) -o (output)
```

## File naming

`lowercase-descriptive-name.drawio` (or `.drawio.png`, `.drawio.svg`, `.drawio.pdf` for exports)

---

## Visual Design Principles

**Architecture diagrams should be DIAGRAM-FIRST: clean flow of icons connected by arrows.**
**Think "AWS reference architecture poster" not "infographic with boxes of text."**

### Design Philosophy

- Icons are the visual anchors. Arrows tell the story.
- Each node = AWS icon (with category fill) + short label below. No text walls.
- White space is good. Don't fill gaps with info boxes.
- Use AWS category colors on icons and matching edges for visual grouping.
- Edges: strokeWidth=1.5 to 2. Clean, not heavy.

---

### 1. Font & Text

- **Always** use `fontFamily=Amazon Ember` on ALL cells.
- Title: `fontSize=16;fontStyle=1;fontColor=#232F3E` (one line, top-left or as group label)
- Service labels: `fontSize=11;fontStyle=1` (bold service name), `fontSize=9;fontColor=#666666` (1-line description)
- Keep labels SHORT. "Amazon S3" + "Training Data" is enough.
- Use `html=1` for multi-line labels with `<b>` and `<font>` tags.

### 2. Color Palette

Use AWS category colors on ICONS. Edges can match the category of their source/target service.

| Category | Icon fillColor | Edge strokeColor | Usage |
|----------|---------------|-----------------|-------|
| General/Dark | `#232F3E` | `#232F3E` | AWS Cloud border, text, user icons |
| AI/ML | `#01A88D` | `#01A88D` | SageMaker, Bedrock |
| Storage | `#3F8624` | `#3F8624` | S3, EFS, FSx |
| Compute | `#D05C17` | `#D05C17` | EC2, ECS, Lambda |
| Database | `#C925D1` | `#C925D1` | DynamoDB, RDS, Aurora |
| Analytics | `#8C4FFF` | `#8C4FFF` | Athena, Glue, Redshift |
| Security | `#DD344C` | `#DD344C` | Cognito, WAF, Secrets Manager |
| Networking | `#8C4FFF` | `#8C4FFF` | VPC, CloudFront, Route 53 |
| DevTools | `#C7131F` | `#C7131F` | CodeCommit, CodePipeline |

**Rules:**
- Icons get their category `fillColor` with `strokeColor=#ffffff`.
- Edges use the category color of the flow (e.g., green for storage flows, teal for ML flows).
- When a diagram has one dominant theme (e.g., all ML), one accent color for all edges is fine.
- Groups/containers: `fillColor=none` with thin borders. Never heavy colored fills on large areas.

### 3. Edge (Arrow) Styling

Edges connect icons. They should be clean and consistent.

```xml
<!-- Standard solid edge -->
<mxCell id="arrow1" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;strokeColor=#01A88D;strokeWidth=2;endArrow=block;endFill=1;" edge="1" source="notebook" target="processing" parent="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Edge label as separate cell (preferred pattern) -->
<mxCell id="arrow1-label" value="&lt;font style=&quot;background-color:#FFFFFF;&quot;&gt;&lt;b&gt;&lt;font color=&quot;#01A88D&quot;&gt;1.&lt;/font&gt;&lt;/b&gt; Launch preprocessing&lt;/font&gt;" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=9;fontColor=#000000;" vertex="1" connectable="0" parent="arrow1">
  <mxGeometry x="-0.1" relative="1" as="geometry">
    <mxPoint as="offset" />
  </mxGeometry>
</mxCell>

<!-- Dashed edge (async, optional, or read-only flow) -->
<mxCell id="arrow-async" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;strokeColor=#3F8624;strokeWidth=2;dashed=1;dashPattern=8 4;endArrow=block;endFill=1;" edge="1" source="s3" target="processing" parent="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- Dashed edge label (italic, category color) -->
<mxCell id="arrow-async-label" value="&lt;font style=&quot;background-color:#FFFFFF;&quot;&gt;&lt;i&gt;&lt;font color=&quot;#3F8624&quot;&gt;Read consent status&lt;/font&gt;&lt;/i&gt;&lt;/font&gt;" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=9;fontColor=#3F8624;" vertex="1" connectable="0" parent="arrow-async">
  <mxGeometry relative="1" as="geometry">
    <mxPoint as="offset" />
  </mxGeometry>
</mxCell>
```

Key rules:
- **strokeWidth=1.5 to 2**. Never above 2.5.
- `endArrow=block;endFill=1` for solid arrowheads.
- `rounded=1` for clean bends on orthogonal edges.
- `dashed=1;dashPattern=8 4` for optional, async, or read-only flows.
- Edge labels: **separate `edgeLabel` cell** with `connectable="0"` and `parent="arrow-id"`.
- Label format: `background-color:#FFFFFF` for readability, step number in bold category color, rest in black.
- Dashed edge labels: italic, in the category color, no step number.
- Use `exitX/exitY` and `entryX/entryY` on edges to control exact connection points on icons.
- Use `<Array as="points">` for waypoints when edges need to route around other elements.

### 4. Flow Step Labels

Format: bold colored number + black text, white background.

```xml
<!-- Numbered step label -->
value="&lt;font style=&quot;background-color:#FFFFFF;&quot;&gt;&lt;b&gt;&lt;font color=&quot;#01A88D&quot;&gt;1.&lt;/font&gt;&lt;/b&gt; Launch preprocessing&lt;/font&gt;"

<!-- Un-numbered label (dashed edges, side flows) -->
value="&lt;font style=&quot;background-color:#FFFFFF;&quot;&gt;&lt;i&gt;&lt;font color=&quot;#3F8624&quot;&gt;Read consent status&lt;/font&gt;&lt;/i&gt;&lt;/font&gt;"
```

- Step number color matches the edge strokeColor.
- Lowercase after number, brief verb phrases.
- fontSize=9, fontColor=#000000 for numbered labels.
- For un-numbered side flows: italic, in category color.

### 5. Service Nodes (Icon + Label)

Each service = icon with proper category fill + short label below.

```xml
<!-- Icon -->
<mxCell id="sagemaker-notebook" value="" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.sagemaker;fillColor=#01A88D;strokeColor=#ffffff;strokeWidth=2;" vertex="1" parent="1">
  <mxGeometry x="110" y="100" width="60" height="60" as="geometry" />
</mxCell>

<!-- Label (separate text cell, positioned below icon) -->
<mxCell id="sagemaker-notebook-label" value="&lt;b&gt;SageMaker Studio Notebook&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=top;spacingTop=2;fontSize=11;fontColor=#000000;fontFamily=Amazon Ember;" vertex="1" parent="1">
  <mxGeometry x="60" y="162" width="160" height="30" as="geometry" />
</mxCell>

<!-- Label with description -->
<mxCell id="s3-label" value="&lt;b&gt;Amazon S3&lt;/b&gt;&lt;br&gt;&lt;font style=&quot;font-size:9px;&quot; color=&quot;#666666&quot;&gt;Training Data&lt;/font&gt;" style="text;html=1;align=center;verticalAlign=top;spacingTop=2;fontSize=11;fontColor=#000000;fontFamily=Amazon Ember;" vertex="1" parent="1">
  <mxGeometry x="60" y="382" width="160" height="40" as="geometry" />
</mxCell>
```

Rules:
- Icon and label are **separate cells** (not verticalLabelPosition on icon).
- Icon size: **60x60** standard.
- Icon style: `fillColor=#CATEGORY_COLOR;strokeColor=#ffffff;strokeWidth=2`
- Label: centered below icon, bold service name (11px), optional 1-line description (9px, #666666).
- Max 2-3 lines in label. No paragraphs.

### 6. Containers / Groups

Light boundaries. No heavy fills.

```xml
<!-- AWS Cloud: solid border, no fill -->
<mxCell id="aws-cloud" value="AWS Cloud" style="points=[];shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_aws_cloud_alt;grStroke=1;verticalLabelPosition=top;verticalAlign=bottom;labelPosition=center;align=center;spacingTop=-4;rounded=1;arcSize=10;strokeColor=#232F3E;fillColor=none;fontStyle=1;fontSize=14;fontColor=#232F3E;strokeWidth=1.5;fontFamily=Amazon Ember;" vertex="1" parent="1">
  <mxGeometry x="30" y="30" width="1050" height="620" as="geometry" />
</mxCell>

<!-- VPC: thin solid green border, no fill -->
<mxCell id="vpc" style="...shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.group_vpc;strokeColor=#248814;fillColor=none;fontColor=#248814;strokeWidth=1;fontFamily=Amazon Ember;..." />

<!-- Subnet: very faint fill, thin border -->
<mxCell style="...grIcon=mxgraph.aws4.group_security_group;strokeColor=#147EB8;fillColor=#E6F2F8;fontColor=#147EB8;strokeWidth=1;..." />
```

Rules:
- AWS Cloud: **solid** border, `strokeWidth=1.5;fillColor=none`. NOT dashed.
- VPC: `strokeWidth=1;fillColor=none` (solid thin green line).
- Subnets: `strokeWidth=1` with very faint fill if needed.
- Custom groups: `strokeWidth=1;fillColor=none`.
- **Never** use solid bright fills on large containers.

### 7. Layout Principles

- **Grid layout**: Arrange icons in rows and columns (e.g., 3 rows x 4 columns).
- **Flow direction**: Left-to-right primary, with vertical sub-flows.
- **Spacing**: ~200px between icon centers horizontally, ~200px vertically.
- **Alignment**: All icons in a row at same Y. All icons in a column at same X.
- **Icon size**: Consistent 60x60 for all service icons.
- **Padding**: 40-60px inside containers.
- **Canvas**: 1200x720 for simple diagrams, 1920x1080 for complex ones.

### 8. What NOT to do

- NO large colored rectangles with paragraphs of text
- NO summary bars, side panels, or benefits boxes (unless explicitly requested)
- NO strokeWidth above 2.5 on anything
- NO transparent/white icon fills (always use AWS category color)
- NO dashed AWS Cloud border (keep solid)
- NO all-same-color monotone diagrams (use category colors)
- NO verbose multi-line descriptions inside or around nodes
- NO circled unicode number badges
- NO heavy fills on group containers

If supplementary info is needed (pricing, tables), add it as a SEPARATE section below the diagram with simple text cells and thin-bordered tables. Keep the architecture area clean.

---

## AWS Architecture Icons (mxgraph.aws4)

**ALWAYS use mxgraph.aws4 icons. Never fall back to generic shapes.**

### Icon template

```xml
<mxCell id="service-id" value="" style="shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.SERVICE;fillColor=#CATEGORY_COLOR;strokeColor=#ffffff;strokeWidth=2;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="60" height="60" as="geometry" />
</mxCell>
```

### Category fillColors

| Category | fillColor |
|----------|-----------|
| General | `#232F3E` |
| AI/ML | `#01A88D` |
| Analytics | `#8C4FFF` |
| Security | `#DD344C` |
| Storage | `#3F8624` |
| Compute | `#D05C17` |
| Database | `#C925D1` |
| Networking | `#8C4FFF` |
| DevTools | `#C7131F` |

### Common resIcon values

| Service | resIcon | Category |
|---------|---------|----------|
| S3 | `s3` | Storage |
| EC2 | `ec2` | Compute |
| Lambda | `lambda` | Compute |
| EKS | `eks` | Compute |
| ECS | `ecs` | Compute |
| Fargate | `fargate` | Compute |
| SageMaker | `sagemaker` | AI/ML |
| Bedrock | `bedrock` | AI/ML |
| DynamoDB | `dynamodb` | Database |
| RDS | `rds` | Database |
| Aurora | `aurora` | Database |
| CloudFront | `cloudfront` | Networking |
| API Gateway | `api_gateway` | Networking |
| ALB | `application_load_balancer` | Networking |
| Route 53 | `route_53` | Networking |
| CloudWatch | `cloudwatch_2` | General |
| Cognito | `cognito` | Security |
| Secrets Manager | `secrets_manager` | Security |
| WAF | `waf` | Security |
| Athena | `athena` | Analytics |
| Redshift | `redshift` | Analytics |
| EMR | `emr` | Analytics |
| Glue | `glue` | Analytics |
| Lake Formation | `lake_formation` | Analytics |
| SNS | `sns` | General |
| SQS | `sqs` | General |
| Step Functions | `step_functions` | General |
| ECR | `ecr` | Compute |
| CodeCommit | `codecommit` | DevTools |
| CodePipeline | `codepipeline` | DevTools |
| NAT Gateway | `nat_gateway` | Networking |
| Internet Gateway | `internet_gateway` | Networking |

### User / External Actor Icons

```xml
<mxCell style="sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;fillColor=#232F3E;strokeColor=none;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=11;fontStyle=0;aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.users;fontFamily=Amazon Ember;" value="Users" vertex="1" parent="1">
  <mxGeometry x="40" y="200" width="48" height="48" as="geometry" />
</mxCell>
```

---

## XML Structure

```xml
<mxfile host="draw.io">
  <diagram name="Diagram Name" id="diagram-id">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1200" pageHeight="720">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- Icons, labels, edges here with parent="1" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

- Use `<mxfile>` wrapper with `<diagram>` for proper draw.io compatibility.
- Unique string `id` values (e.g. `"s3-data"`, `"arrow1"`, `"arrow1-label"`).
- Icons and labels as separate cells (icon = shape, label = text below).
- Edges reference `source` and `target` icon IDs.
- Edge labels as child cells with `connectable="0"` and `parent="edge-id"`.
- Align to grid (multiples of 10).

## Edge Routing

- `edgeStyle=orthogonalEdgeStyle;rounded=1` for right-angle connectors.
- `exitX/exitY` and `entryX/entryY` (0 to 1) for precise connection points.
- `<Array as="points"><mxPoint x="300" y="150"/></Array>` for waypoints.
- Route long-span edges above or below the main flow area.

## CRITICAL: XML well-formedness

- NEVER use double hyphens inside XML comments
- Escape: `&amp;`, `&lt;`, `&gt;`, `&quot;`
- Use single-quoted `'EOF'` in `cat << 'EOF'` to prevent shell expansion
- Always use unique `id` values
- Use `&quot;` inside style attribute values within HTML labels
