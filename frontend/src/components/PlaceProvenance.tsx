/**
 * The place-provenance pair (ORD-B): whose fact this is, and in which coordinate
 * system the numbers on this card mean anything.
 *
 * Two rules hold this component together:
 *  - A row is never dropped. A missing value shows a placeholder that names *which*
 *    fact is absent, because a field that disappears teaches the traveller nothing.
 *  - A row is only anchored when it carries a value the server actually sent (Q70:
 *    the anchor is the contract field name, same convention as `CnxMeasuredFacts`).
 *    A placeholder is our own word, not a reading, so it gets no anchor.
 */

import { useLocale } from "../i18n/LocaleContext";
import { provenanceCopy } from "../i18n/placeProvenanceCopy";

type Props = {
  /** The place's own name, as the server sent it. */
  name: string;
  category?: string | null;
  providerKey?: string | null;
  coordinateSystem?: string | null;
  sourceCoordinateSystem?: string | null;
  host?: string | null;
};

function Field({
  label,
  field,
  value,
  missing,
}: {
  label: string;
  field: string;
  value: string | null;
  missing: string;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd
        data-testid={`place-provenance-${field}`}
        {...(value === null ? {} : { "data-cnx-field": field, "data-cnx-value": value })}
      >
        {value ?? missing}
      </dd>
    </div>
  );
}

function present(value?: string | null): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function PlaceProvenance({
  name,
  category,
  providerKey,
  coordinateSystem,
  sourceCoordinateSystem,
  host,
}: Props) {
  const { locale } = useLocale();
  const c = provenanceCopy(locale);
  const source = present(providerKey);
  const summary = [category, source ?? c.noSource].filter(Boolean).join(" · ");

  return (
    <details data-testid="place-provenance">
      <summary data-testid="place-provenance-summary">{summary}</summary>
      <dl className="trial-review activity-facts">
        <Field label={c.name} field="name" value={present(name)} missing={c.noName} />
        <Field
          label={c.source}
          field="provider_key"
          value={source}
          missing={c.noSource}
        />
        <Field
          label={c.coordinateSystem}
          field="coordinate_system"
          value={present(coordinateSystem)}
          missing={c.noCoordinateSystem}
        />
        <Field
          label={c.sourceCoordinateSystem}
          field="source_coordinate_system"
          value={present(sourceCoordinateSystem)}
          missing={c.noSourceCoordinateSystem}
        />
        <Field
          label={c.host}
          field="opening_hours.source_urls"
          value={present(host)}
          missing={c.noHost}
        />
      </dl>
    </details>
  );
}
