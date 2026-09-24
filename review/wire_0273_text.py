import io

p = 'frontend/src/app/V8Experience.tsx'
t = io.open(p, encoding='utf-8', newline='').read()

old = '''    } catch (error) {
      /* The scene read itself failed: named and fail-closed, never a creation. */
      setSealedDemoUnavailable(
        error instanceof Error
          ? `${locale === "zh-CN" ? "没读到封存演示的信息" : "The sealed demo could not be read"}: ${error.message}`
          : t("shell.loadError"),
      );
    } finally {'''
new = '''    } catch (error) {
      /* ORD-0273-TEXT: the user sentence comes from an i18n key -- the raw error.message (with its
         MIME/content-type and error shapes) must not reach the main copy.  The technical facts stay
         available to telemetry through the data-* attributes on the wizard's alert element. */
      setSealedDemoUnavailable(t("trial.sealedUnreadable"));
      setSealedDemoDetail(
        error instanceof Error
          ? { message: error.message, name: error.name }
          : { message: String(error), name: "Unknown" },
      );
    } finally {'''
assert t.count(old) == 1
t = t.replace(old, new)

# Add the detail state next to sealedDemoUnavailable.
state_anchor = 'const [sealedDemoUnavailable, setSealedDemoUnavailable] = useState<string | null>(null);'
state_add = state_anchor + '''
  /* ORD-0273: the technical shape of the sealed-demo read failure (raw message + error name).
     Rendered only inside data-* on the wizard's alert -- a diagnosable fact, not user copy. */
  const [sealedDemoDetail, setSealedDemoDetail] = useState<{ message: string; name: string } | null>(null);'''
assert t.count(state_anchor) == 1
t = t.replace(state_anchor, state_add)

# Pass the technical detail down so it lands in data-* on the alert element.
prop_anchor = 'sealedDemoUnavailable={sealedDemoUnavailable}'
prop_add = prop_anchor + '\n          sealedDemoDetail={sealedDemoDetail}'
assert t.count(prop_anchor) == 1
t = t.replace(prop_anchor, prop_add)

io.open(p, 'w', encoding='utf-8', newline='').write(t)
print('TEXT half wired')
