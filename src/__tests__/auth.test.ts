import { z } from 'zod';
import assert from 'assert';

const loginSchema = z.object({
  email: z.string().email("Noto'g'ri email formati kiritildi"),
  password: z
    .string()
    .min(8, "Parol kamida 8 ta belgidan iborat bo'lishi kerak")
    .regex(/[A-Z]/, "Parolda kamida 1 ta katta harf bo'lishi kerak")
    .regex(/[0-9]/, "Parolda kamida 1 ta raqam bo'lishi kerak"),
});

export function runAuthValidationTests(): boolean {
  const valid = loginSchema.safeParse({
    email: 'admin@maktab142.uz',
    password: 'AdminPassword123!',
  });
  assert.strictEqual(valid.success, true);

  const invalidShort = loginSchema.safeParse({
    email: 'admin@maktab142.uz',
    password: 'Pass1',
  });
  assert.strictEqual(invalidShort.success, false);

  const invalidNoNum = loginSchema.safeParse({
    email: 'admin@maktab142.uz',
    password: 'PasswordOnly',
  });
  assert.strictEqual(invalidNoNum.success, false);

  const invalidNoUpper = loginSchema.safeParse({
    email: 'admin@maktab142.uz',
    password: 'password123',
  });
  assert.strictEqual(invalidNoUpper.success, false);

  return true;
}

if (typeof require !== 'undefined' && require.main === module) {
  runAuthValidationTests();
  console.log('✓ All frontend auth validation tests passed!');
}
